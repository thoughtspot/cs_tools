class TableSecurityInfo {
    //
    constructor(divId, guid, name, currentlySelectedUserGroups, showMessage) {
        this.divId = divId;
        this.guid = guid;
        this.name = name;
        this.currentlySelectedUserGroups = currentlySelectedUserGroups;
        // looks like..
        // {
        //     <USER_GROUP_GUID>: <USER_GROUP_NAME>
        // }
        this._tableAccess = {};
        // looks like..
        // {
        //     <USER_GROUP_GUID>: <PERMISSION>
        // }
        this._columnAccess = {};
        // looks like..
        // {
        //     <COLUMN_GUID>: {
        //         "columnName": <COLUMN_NAME>,
        //         "permissions": {
        //             <USER_GROUP_GUID>: {
        //                 "userGroupName": <USER_GROUP_NAME>,
        //                 "access": <SHARE_MODE>
        //             }
        //         }
        //     }
        // }
        this._showMessage = showMessage;
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
                self._columnAccess[columnData.id] = {
                    'columnName': columnData.name,
                    'permissions': {}  // set in getCLS()
                }
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

            $.each(self._columnAccess, function(columnGuid, columnData) {
                clsData[columnGuid] = {
                    'columnName': columnData.columnName,
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
        var matrixDiv = $(this.divId)

        // Clear our security matrix
        matrixDiv.empty();

        // Add the "Update Security" & "Row Headers" column first
        matrixDiv.append(
            '<div class="row-header">' +
            '  <div id="update-security">Update Security</div>' +
            '  <div id="select-all-columns">Select All Columns</div>' +
            '</div>'
        );

        $.each(
            this._columnAccess,
            function(columnGuid, clsData) {
                $('.row-header').append('<div>' + clsData.columnName + '</div>')
            }
        );

        // Add UserGroup Columns, one by one
        $.each(
            this.currentlySelectedUserGroups,
            function(userGroupGuid, userGroupName) {
                new SelectorSecurityAccess(
                    self.divId,
                    userGroupGuid,
                    userGroupName,
                    self._columnAccess
                ).generateHTML();
            }
        );

        // $('#progress-loader').loadingOverlay('remove');

        $('#update-security').click(function() {
            // $('#progress-loader').loadingOverlay({
            //     loadingText: 'Applying security...'
            // });

            self.updateTSSecurity();
            self.refresh();
        });
    }

    updateTSSecurity() {
        var self = this;
        this.optimizeMatrix();

        // Update security below
        var clearPermissions = {}

        // Build clearing permissions list
        $.each(this.currentlySelectedUserGroups, function(userGroupGuid, userGroupName) {
            clearPermissions[userGroupGuid] = {'shareMode': 'NO_ACCESS'};
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
                type: 'LOGICAL_TABLE',
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
                type: 'LOGICAL_COLUMN',
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
                shareMode: permission
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
                    type: 'LOGICAL_TABLE',
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
                if (columnData.columnMapping == setName) {
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
                    type: 'LOGICAL_COLUMN',
                    guids: columnGuidsToApplyCLS,
                    permissions: permissions,
                }),
                xhrFields: {
                    withCredentials: true
                },
                async: false
            })
        });

        // Small tables are quite quick, so at least show the message for 2 seconds
        setTimeout(function() {
            // $('#progress-loader').loadingOverlay('remove');
            self._showMessage(true, 'Security has been updated!', 'All security has been successfully updated.');
        }, 2000);
    }

    optimizeMatrix() {
        var self = this;
        var n_columns = Object.keys(this._columnAccess).length

        this._tableAccess = {};

        // loop through each column and access-level button sub-columns
        $(this.divId + ' .column').each(function () {
            var thisColumn = $(this);
            var userGroupGuid = $(this).attr('id');

            $.each(['NO_ACCESS', 'READ_ONLY', 'MODIFY'], function(_, accessLevel) {
                var n_active_columns = thisColumn.children('.column-data').children().filter('.' + accessLevel + '.active').length;

                // if we find that the length of a single access-level actives equals
                // the total number of columns, then the whole table should be shared
                if ( n_active_columns == n_columns ) {
                    self._tableAccess[userGroupGuid] = accessLevel;

                    // for good measure, remove the cls rules for these columns as well
                    $.each(self._columnAccess, function(columnGuid, columnData) {
                        delete columnData.permissions[userGroupGuid];
                    });

                    // terminate accessLevel inner loop early
                    return false;
                }
            })
        });

        // Create unique key to reduce API usage
        $.each(self._columnAccess, function(columnGuid, columnData) {
            var columnMapping = '';

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
        this._columnAccess[columnGuid].permissions[userGroupGuid].access = access;
    }
}



// INTERACTIVE ELEMENTS

$.widget("ts.messageDialog", $.ui.dialog, {
    //
    options: {
        position: { my: "center", at: "center", of: "#content" },
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
            $(self.divId).select2({multiple: true, placeholder: 'select groups'});
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
            $(self.divId).select2({placeholder: 'select a table'});
        })
        .fail(function(xhr, textStatus, errorThrown) {
            $(self.divId).parent('.menu-option').hide();
            $('<div id="error-message" title="Failed to retrieve table names"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>API called returned code: ' + error.status + '</p></div>').messageDialog({ dialogClass: 'error-message' });
            console.error(errorThrown)
        });
    }
}

class SelectorSecurityAccess {

    constructor (matrixDiv, userGroupGuid, userGroupName, clsData) {
        this._matrixDiv = matrixDiv;
        this._userGroupGuid = userGroupGuid;
        this._userGroupName = userGroupName;
        this._clsData = clsData;
        this.divId = userGroupGuid;
    }

    generateHTML () {

        // build up the basic structure
        $(this._matrixDiv).append(
            '<div class="column" id="' + this.divId + '">' +
            '  <div class="column-header">' + this._userGroupName + '</div>' +
            '  <div class="select-all-columns"></div>' +
            '  <div class="column-data"></div>' +
            '</div>'
        );

        var self = this;
        var row = 0;
        var buttons = {'NO_ACCESS': 'lock', 'READ_ONLY': 'eye', 'MODIFY': 'pencil-square'};

        // add select-all-columns buttons
        $.each(buttons, function(accessLevel, icon) {
            self.addButton(
                $('#' + self.divId + ' .select-all-columns'),
                row,
                accessLevel,
                icon,
                '',  // active flag is never on
                ''
            );
        });

        // add individual row buttons
        $.each(this._clsData, function(columnGuid, columnAccessData) {
            row++;
            var selector = '#' + self.divId + ' .column-data';

            $.each(buttons, function(accessLevel, icon) {
                self.addButton(
                    selector,
                    row,
                    accessLevel,
                    icon,
                    (columnAccessData.permissions[self._userGroupGuid].access == accessLevel) ? ' active' : '',
                    columnGuid
                );
            });
        });

        // set up click handling
        $('#' + self.divId + ' .column-data > .matrix-cell').click(function(e) { self.onlyOneSelected(e) });
        $('#' + self.divId + ' .select-all-columns > .matrix-cell').click(function(e) { self.selectWholeColumn(e) });
    }

    addButton (selectorPattern, rowNo, accessLevel, icon, active, columnGuid) {
        //
        $(selectorPattern).append(
            '<div class="matrix-cell row-' + rowNo + ' ' + accessLevel + active + '">' +
            '  <i class="bi bi-' + icon + '"></i>' +
            '</div>'
         );

        // attach column GUID information to each button if it's not a select-all-button
        $(selectorPattern).children().each(function () {
            if ( rowNo > 0 && $(this).hasClass('row-' + rowNo) ) {
                $(this).attr('data-column-guid', columnGuid)
            }
         });
    }

    selectWholeColumn (event) {
      //
      event.preventDefault();
      var thisDiv = $(event.target).closest('div');
      var accessLevel = thisDiv.attr('class').split(' ').slice(-1)[0];
      
      thisDiv.parent().next().children().each(function() {
        if ( $(this).hasClass(accessLevel) ) {
          this.click();
        }
      })
    }

    onlyOneSelected (event) {
      //
      //
      //
      var thisDiv = $(event.target).closest('div');

      // .active will allow the element to be highlighted, but let's allow the
      thisDiv.addClass('active');

      var thisDivClasses = thisDiv.attr('class').split(' ');
      var thisDivAccessLevel = thisDivClasses[2];  // NO_ACCESS, READ_ONLY, MODIFY
      var thisRowClass = thisDivClasses[1];        // row-1, row-2, ...
      var columnGuid = thisDiv.attr('data-column-guid');
      
      // Great, now that we've made our selection, de-select anything
      // else in this column's row.
      $(thisDiv).siblings().each(
        function() {
          if ( $(this).hasClass(thisRowClass) ) {
            $(this).removeClass('active');
          }
        }
      );

      // set the column access level
      this._clsData[columnGuid].permissions[this._userGroupGuid].access = thisDivAccessLevel;
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
        // $('#progress-loader').loadingOverlay({
        //     loadingText: 'Loading security...'
        // });

        this.tableSecurityInfo = new TableSecurityInfo(
            '#security-matrix',
            $('#select-tablename').val(),
            $("#select-tablename option:selected").text(),
            this.selectorUserGroups.getSelectedUserGroups(),
            this._showMessage
        );

        this.tableSecurityInfo.refresh();
    }

    _showMessage(success, title, message) {
        var successMessage = '<div id="success-message" title="' + title + '"><p><span class="ui-icon ui-icon-circle-check" style="float:left; margin:0 7px 50px 0;"></span>' + message + '</p></div>';
        var errorMessage = '<div id="error-message" title="' + title + '"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>' + message + '</p></div>';
        if (success) {
            $(successMessage).messageDialog({ dialogClass: 'success-message' });
        } else {
            $(errorMessage).messageDialog({ dialogClass: 'error-message' });
        }
    }
}


$(document).ready(function() {
    const app = new Application().init()
});
