class TableSecurityInfo {
    //
    constructor(guid, name, currentlySelectedUserGroups, divId) {
        this.divId = divId;
        this.guid = guid;
        this.name = name;
        this.currentlySelectedUserGroups = currentlySelectedUserGroups;
        this._tableAccess = {};
        this._columnAccess = {};
    }

    refresh() {
        this._tableAccess = {};
        this.getTablePermissions();
        this.getTableColumns();
        this.getCLS();

        if (this.divId != "") {
            this.generateHTML();
        }
    }

    getTablePermissions() {
        var self = this;

        $.ajax({
            url: '/api/defined_permission',
            type: 'POST',
            dataType: 'JSON',
            contentType: 'application/json',
            data: JSON.stringify({
                type: "LOGICAL_TABLE",
                guids: [this.guid]
            }),
            xhrFields: {
                withCredentials: true
            },
            async: false
        })
        .done(function(data, textStatus, xhr) {
            $.each(data[self.guid].permissions, function(userGroupGuid, permissionData) {
                self._tableAccess[userGroupGuid] = permissionData.shareMode;
            });
        })
        .fail(function(xhr, textStatus, errorThrown) {
            console.error(errorThrown)
        });
    }

    getTableColumns() {
        var self = this;

        $.ajax({
            url: '/api/list_columns/' + this.guid,
            type: 'GET',
            dataType: 'JSON',
            xhrFields: {
                withCredentials: true
            },
            async: false
        })
        .done(function(data, textStatus, xhr) {
            $.each(data.headers, function(index, columnData) {
                self._columnAccess[columnData.id] = columnData.name;
            });
        })
        .fail(function(xhr, textStatus, errorThrown) {
            console.error(errorThrown)
        });
    }

    getCLS() {
        var self = this;

        $.ajax({
            url: '/api/defined_permission',
            type: 'POST',
            dataType: 'JSON',
            contentType: 'application/json',
            data: JSON.stringify({
                type: "LOGICAL_COLUMN",
                guids: Object.keys(this._columnAccess)
            }),
            xhrFields: {
                withCredentials: true
            },
            async: false
        })
        .done(function(data, textStatus, xhr) {
            var clsData = {}

            $.each(self._columnAccess, function(columnGuid, columnName) {
                clsData[columnGuid] = {
                    'columnName': columnName,
                    'permissions': {}
                }

                $.each(self.currentlySelectedUserGroups, function(userGroupGuid, userGroupData) {
                    // 1) first set the column permissions if they are defined.
                    var setAccess = null;

                    if (!jQuery.isEmptyObject(data[columnGuid].permissions) && ($.inArray(userGroupGuid, Object.keys(data[columnGuid].permissions)) != -1)) {
                        setAccess = data[columnGuid].permissions[userGroupGuid].shareMode;
                    }

                    // 2) if table level permissions are set then set these (and possibly overriding CLS, like TS would do)
                    if ($.inArray(userGroupGuid, Object.keys(self._tableAccess)) != -1) {
                        setAccess = self._tableAccess[userGroupGuid];
                    }

                    // 3) otherwise set permissions to "no access"
                    if (setAccess == null) {
                        setAccess = 'NO_ACCESS';
                    }

                    // Set the permission in the object
                    clsData[columnGuid].permissions[userGroupGuid] = {
                        userGroupName: userGroupData,
                        access: setAccess
                    };

                    // Overlaps between CLS and table rules will be cleaned up when syncing back to TS
                });
            });

            self._columnAccess = clsData;
        })
        .fail(function(xhr, textStatus, errorThrown) {
            console.error(errorThrown)
        });
    }

    generateHTML() {
        var self = this;
        var rowNo = 0;
        var colNo = 0;

        $(this.divId).empty();

        //------------------------------
        // Add user group headers
        //------------------------------
        $(this.divId).append('<div class="matrix-row user-group-header"></div>');
        $(this.divId + ' .user-group-header').append('<div class="matrix-cell"></div>');

        $.each(this.currentlySelectedUserGroups, function(userGroupGuid, userGroupName) {
            $(self.divId + ' .user-group-header').append('<div class="matrix-cell">' + userGroupName + '</div>');
        });

        //------------------------------
        // Add the 'select all' headers
        //------------------------------
        $(this.divId).append('<div class="matrix-row selector-all-headers"></div>');
        $(this.divId + ' .selector-all-headers').append('<div class="matrix-cell"><b>Apply to all</b></div>');

        $.each(this.currentlySelectedUserGroups, function(userGroupGuid, userGroupName) {
            colNo++

            var onButtonClicked = function(event) {
                var checkAllColumnsHTMLId = $('#check-all-col-' + userGroupGuid).data('colNo');
                var clickSameColumnButton = function() {
                    $(this).children('.' + $(event.target).data('buttonValue')).trigger('click');
                }

                $('.cls-selectors.col-' + checkAllColumnsHTMLId).each(clickSameColumnButton);
            }

            new SelectorTSSecurityAccess(
                self.divId + ' .selector-all-headers',
                '#check-all-col-' + userGroupGuid,
                rowNo,
                colNo,
                [],
                onButtonClicked,
                null
            ).generateHTML();
        });

        //------------------------------
        // Add the cls entries
        //------------------------------
        $.each(this._columnAccess, function(columnGuid, clsData) {
            rowNo++;
            colNo = 0;

            $(self.divId).append('<div class="matrix-row permission-rows row-' + rowNo + '"><div class="matrix-cell">' + clsData.columnName + '</div></div>');

            $.each(clsData.permissions, function(userGroupGuid, _) {
                colNo++;

                var onButtonClicked = function(event) {
                    event.preventDefault();
                    self.setAccess(columnGuid, userGroupGuid, $(event.target).data('buttonValue'));    
                }

                new SelectorTSSecurityAccess(
                    self.divId + ' .permission-rows.row-' + rowNo,
                    '#' + columnGuid + '_' + userGroupGuid,
                    rowNo,
                    colNo,
                    ['cls-selectors'],
                    onButtonClicked,
                    self.getAccess(columnGuid, userGroupGuid)
                ).generateHTML();
            });
        });

        $('#progress-loader').loadingOverlay('remove');

        //------------------------------
        // Add the update button
        //------------------------------
        $(self.divId).append('<div id="update-security">Update Security</div>');
        $('#update-security').click(function() {
            $('#progress-loader').loadingOverlay({
                loadingText: 'Applying security...'
            });

            self.updateTSSecurity();
        });
    }

    updateTSSecurity() {
        var self = this;
        this.optimizeMatrix();

        // Now update the TS Security
        var clearPermissions = {}

        // Build clearing permissions list
        $.each(this.currentlySelectedUserGroups, function(userGroupGuid, userGroupName) {
            clearPermissions[userGroupGuid] = {"shareMode": "NO_ACCESS"};
        });

        // NOTE: gotta find Bill's work and fix that too


        // 1) clear all existing security
        // a) clear all table level rules
        $.ajax({
            url: '/api/security/share',
            type: 'POST',
            dataType: 'JSON',
            contentType: 'application/json',
            data: JSON.stringify({
                type: "LOGICAL_TABLE",
                guids: [this.guid],
                permissions: clearPermissions,
            }),
            xhrFields: {
                withCredentials: true
            },
            async: false
        });

        // b) clear all CLS rules
        $.ajax({
            url: '/api/security/share',
            type: 'POST',
            dataType: 'JSON',
            contentType: 'application/json',
            data: JSON.stringify({
                type: "LOGICAL_COLUMN",
                guids: Object.keys(this._columnAccess),
                permissions: clearPermissions,
            }),
            xhrFields: {
                withCredentials: true
            },
            async: false
        });

        // 2) apply table level rules
        var userGroupAccess = {};

        $.each(this._tableAccess, function(userGroupGuid, permission) {
            userGroupAccess[userGroupGuid] = {
                "shareMode": permission
            }
        });

        // if we have permissions to apply, do that first
        if (!jQuery.isEmptyObject(userGroupAccess)) {
            $.ajax({
                url: '/api/security/share',
                type: 'POST',
                dataType: 'JSON',
                contentType: 'application/json',
                data: JSON.stringify({
                    type: "LOGICAL_TABLE",
                    guids: [this.guid],
                    permissions: userGroupAccess,
                }),
                xhrFields: {
                    withCredentials: true
                },
                async: false
            });
        }

        // 3) Apply CLS rules
        var uniqueSets = [];

        $.each(self._columnAccess, function(columnGuid, columnData) {
            if (($.inArray(columnData.columnMapping, uniqueSets) == -1) && (columnData.columnMapping != '')) {
                uniqueSets.push(columnData.columnMapping);
            }
        });

        $.each(uniqueSets, function(index, setName) {
            var columnGuidsToApplyCLS = [];
            var permissions = {};

            $.each(self._columnAccess, function(columnGuid, columnData) {
                if (columnData.cMap == setName) {
                    columnGuidsToApplyCLS.push(columnGuid);

                    $.each(columnData.permissions, function(userGroupGuid, userGroupData) {
                        permissions[userGroupGuid] = {
                            shareMode: userGroupData.access
                        }
                    })
                }
            });

            $.ajax({
                url: '/api/security/share',
                type: 'POST',
                dataType: 'JSON',
                contentType: 'application/json',
                data: JSON.stringify({
                    type: "LOGICAL_COLUMN",
                    id: columnGuidsToApplyCLS,
                    permissions: permissions,
                }),
                xhrFields: {
                    withCredentials: true
                },
                async: false
            })
        });

        // Small tables are quite quick, so at least show the message for 2 seconds
        setTimeout(
            function() {
                $('#progress-loader').loadingOverlay('remove');
                // self._showMessage(true, 'Security has been updated!', 'All security has been successfully updated.');
            },
            2000
        );
    }

    optimizeMatrix() {
        var self = this;
        var colNo = 1;

        // Clear all table access rules
        self._tableAccess = {};

        // Set the new table access rules
        $.each(this.currentlySelectedUserGroups, function(userGroupGuid, userGroupName) {
            $.each(['NO_ACCESS', 'READ_ONLY', 'MODIFY'], function(index, accessType) {
                if ($('.cls-selectors.col-' + colNo + ' .access-selector.' + accessType + '.Active').length == $('.cls-selectors.col-' + colNo).length) {
                    self._tableAccess[userGroupGuid] = accessType;

                    // Remove all cls rules for these columns
                    $.each(self._columnAccess, function(columnGuid, columnData) {
                        delete columnData.permissions[userGroupGuid];
                    });

                    return false;
                }
            });

            if ($.inArray(userGroupGuid, Object.keys(self._tableAccess)) == -1) {
                // remove table access rule
                delete self._tableAccess[userGroupGuid];
            }

            colNo++;
        });

        // Create unique key to reduce API
        $.each(self._columnAccess, function(columnGuid, columnData) {
            var columnMapping = "";

            $.each(columnData.permissions, function(userGroupGuid, accessData) {
                columnMapping = columnMapping + '|' + accessData.access;
            });

            columnData['columnMapping'] = columnMapping;
        });
    }

    getAccess(columnGuid, userGroupGuid) {
        var access = this._columnAccess[columnGuid].permissions[userGroupGuid].access;
        return (access == null) ? 'NO_ACCESS' : access;
    }

    setAccess(columnGuid, userGroupGuid, access) {
        // NOTE: Error here ... probably in how we store the columnAccess data.
        //
        // console.log(columnGuid, userGroupGuid, access)
        // console.log(this._columnAccess)
        this._columnAccess[columnGuid].permissions[userGroupGuid].access = access;
    }
}

// INTERACTIVE ELEMENTS

$.widget("ts.messageDialog", $.ui.dialog, {
    //
    options: {
        position: { my: "center", at: "center", of: "#security-container" },
        modal: true,
        buttons: {
            OK: function() {
                $(this).messageDialog("close");
            }
        }
    }
});

class SelectorUserGroups {
    // The User-Groups selector is a multi-select dropdown which allows the
    // user to determine which ThoughtSpot Groups to get security permissions
    // for.
    constructor(id) {
        this._allUserGroups = {};
        this.divId = id;
    }

    getSelectedUserGroups() {
        // Return a mapping of user-groups that have been selected by the user
        var self = this;
        var selectedGroups = $.extend(true, {}, this._allUserGroups);

        $.each(selectedGroups, function(guid, data) {
            if ($.inArray(guid, $(self.divId).val()) == -1) {
                delete selectedGroups[guid];
            }
        });

        return selectedGroups;
    }

    generateHTML() {
        var self = this;

        $.ajax({
            url: '/api/user_groups',
            type: 'GET',
            dataType: 'JSON',
            xhrFields: {
                withCredentials: true
            },
            async: false
        })
        .done(function(data, textStatus, xhr) {
            var HTML = '';

            $.each(data, function(k, userGroup) {
                if ($.inArray(userGroup.name, ['Administrator', 'System', 'All']) == -1) {
                    HTML += '<option value="' + userGroup.id + '">' + userGroup.name + '</option>';

                    // additionally: track the user-groups that we've seen thus far
                    self._allUserGroups[userGroup.id] = userGroup.name;
                }
            });

            $(self.divId).append(HTML);
            $(self.divId).multiselect();
        })
        .fail(function(xhr, textStatus, errorThrown) {
            $(self.divId).parent('.menu-option').hide();
            $('<div id="error-message" title="Failed to retrieve user groups"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>API call returned code: ' + error.status + '</p></div>').messageDialog({ dialogClass: 'error-message' });
            console.error(errorThrown)
        });
    }
}

class SelectorTables {
    // The tables selector is a dropdown which allows the user to determine
    // which table to get security permissions for.
    constructor(id) {
        this.divId = id;
    }

    generateHTML() {
        var self = this;

        $.ajax({
            url: '/api/tables',
            type: 'GET',
            dataType: 'JSON',
            xhrFields: {
                withCredentials: true
            },
            async: false
        })
        .done(function(data, textStatus, xhr) {
            var HTML = '';
            $.each(data, function(k, table) {
                HTML += '<option value="' + table.id + '">' + table.name + '</option>'
            })
            $(self.divId).append(HTML);
            $(self.divId).selectmenu();
        })
        .fail(function(xhr, textStatus, errorThrown) {
            $(self.divId).parent('.menu-option').hide();
            $('<div id="error-message" title="Failed to retrieve table names"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>API called returned code: ' + error.status + '</p></div>').messageDialog({ dialogClass: 'error-message' });
            console.error(errorThrown)
        });
    }
}

class SelectorTSSecurityAccess {

    constructor(elementAttrs, divId, rowNo, colNo, extraClasses, onButtonClick, setValue) {
        this.elementAttrs = elementAttrs;
        this.divId = divId;
        this.rowNo = rowNo;
        this.colNo = colNo;
        this.extraClasses = extraClasses;
        this.onButtonClick = onButtonClick;
        this.setValue = setValue;
    }

    generateHTML() {
        this.addMainDiv();
        this.addButton('NO_ACCESS');
        this.addButton('READ_ONLY');
        this.addButton('MODIFY');
    }

    addMainDiv() {
        var self = this;
        var justTheId = this.divId.substring(1);

        $(this.elementAttrs).append('<div class="matrix-cell"><div id="' + justTheId + '" class="access-selector-group row-' + this.rowNo + ' col-' + this.colNo + ' ' + this.extraClasses.join(' ') + '"></div></div>');
        $(this.divId).data({'colNo': this.colNo, 'rowNo': this.rowNo});
        $(this.divId).click(function(event) { self.onlyOneSelected(event) });
    }

    addButton(buttonClass) {
        var isActive = ((this.setValue == buttonClass) ? ' Active' : '');
        $(this.divId).append('<button class="access-selector ' + buttonClass + isActive + '"></button>');        
        $(this.divId + ' .' + buttonClass).data({'buttonValue': buttonClass});
    }

    onlyOneSelected(event) {
        event.preventDefault();
        $(event.target).siblings().removeClass('Active');
        $(event.target).addClass('Active');
        this.onButtonClick(event);
    }
}


// MAIN APPLICATION

class Application {

    constructor() {
        this.selectorUserGroups = new SelectorUserGroups('#select-user-groups');
        this.selectorTables = new SelectorTables('#select-tablename');
        this.tableSecurityInfo = null;
    }

    init() {
        // setup the basic UI elements
        this.selectorUserGroups.generateHTML();
        this.selectorTables.generateHTML();
        $("#btn-get-permissions").click(this.getPermissions.bind(this));
    }

    getPermissions() {
        $('#progress-loader').loadingOverlay({
            loadingText: 'Loading security...'
        });

        this.tableSecurityInfo = new TableSecurityInfo(
            $('#select-tablename').val(),
            $("#select-tablename option:selected").text(),
            this.selectorUserGroups.getSelectedUserGroups(),
            '#security-matrix',
        );

        this.tableSecurityInfo.refresh();
    }
}


$(document).ready(function() {
    const app = new Application().init()
});
