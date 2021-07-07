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
        // this.getTableColumns();
        // this.getCLS();
        // if (this.divId != "") {
        //     this.generateHTML();
        // }
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
                id: [this.guid]
            }),
            xhrFields: {
                withCredentials: true
            },
            async: false
        })
        // .done(function(data, textStatus, xhr) {
        //     $.each(data[self.guid].permissions, function(userGroupGuid, permissionData) {
        //         self._tableAccess[userGroupGuid] = permissionData.shareMode;
        //     });
        // })
        // .fail(function(xhr, textStatus, errorThrown) {
        //     console.error(errorThrown)
        // });
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
        $("#btn-get-permissions").click(this._getPermissions.bind(this));
    }

    _getPermissions() {
        // TODO
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

    // _showMessage(success, title, message) {
    //     var successMessage = '<div id="success-message" title="' + title + '"><p><span class="ui-icon ui-icon-circle-check" style="float:left; margin:0 7px 50px 0;"></span>' + message + '</p></div>';
    //     var errorMessage = '<div id="error-message" title="' + title + '"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>' + message + '</p></div>';
    //     if (success) {
    //         $(successMessage).messageDialog({ dialogClass: 'success-message' });
    //     } else {
    //         $(errorMessage).messageDialog({ dialogClass: 'error-message' });
    //     }
    // }
}


$(document).ready(function() {
    const app = new Application().init()
});
