function showMessage(success, title, message) {
    var successMessage = '<div id="success-message" title="' + title + '"><p><span class="ui-icon ui-icon-circle-check" style="float:left; margin:0 7px 50px 0;"></span>' + message + '</p></div>';
    var errorMessage = '<div id="error-message" title="' + title + '"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>' + message + '</p></div>';
    if (success) {
        $(successMessage).messageDialog({
            dialogClass: 'success-message'
        });
    } else {
        $(errorMessage).messageDialog({
            dialogClass: 'error-message'
        });
    }
}


class Application {

    constructor() {
        this._tsTableSecurity = null;
        // this._userGroupSelector = new TSSelectUserGroups("selUserGroups");
        // this._tableSelector = new TSSelectTable("tableName");
    }

    init() {
        console.log('Initialising application....')
        var self = this;
        $("#getPermissions").click(this._getPermissions.bind(this));
    }

    _getPermissions(event) {
        $('#progressLoader').loadingOverlay({
            loadingText: 'Loading security...'
        });

        // this._tsTableSecurity = new TSTableSecurity(
        //     $('#tableName').val(),
        //     $("#tableName option:selected").text(),
        //     this._userGroupSelector.getSelectedUserGroups(),
        //     '#securityMatrix',
        //     this._showMessage
        // );
    }
}


// ON_READY
$(document).ready(
    function() {
        console.log('DOM ready...');
        const app = new Application().init()
    }
);
