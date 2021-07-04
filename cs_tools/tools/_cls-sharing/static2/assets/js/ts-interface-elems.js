/*
 * ==================================================================================================================================
 * 
 * Copyright (c) 2021 ThoughtSpot
 * 
 * ----------------------------------------------------------------------------------------------------------------------------------
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
 * files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy,
 * modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 *  OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
 *  BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
 *  OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 * 
 * ----------------------------------------------------------------------------------------------------------------------------------
 * Last Modified: Thursday June 17th 2021 9:56:56 am
 * ==================================================================================================================================
 */
/* Message/Error Dialog */
$.widget("ts.messageDialog", $.ui.dialog, {
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

class TSSelectTable {
    constructor(divElem) {
        this._divElem = divElem;
        this._generateHTML();
    }

    _generateHTML() {
        var self = this;

        new TSGetTablesRequest(
            function(data) {
                console.log('Successfully retrieved table names from ThoughtSpot...');
                var optionsHTML = '';
                $.each(data, function(key, entry) {
                    optionsHTML += '<option value="' + entry.id + '">' + entry.name + '</option>'
                })
                $('#' + self._divElem).append(optionsHTML);
                $("#" + self._divElem).selectmenu();
            },
            function(error) {
                $("#" + self._divElem).parent('.menuOption').hide();
                $('<div id="error-message" title="Failed to retrieve table names"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>API called returned code: ' + error.status + '</p></div>').messageDialog({ dialogClass: 'error-message' });
                console.log('FAILED to retrieve table names from ThoughtSpot');
                console.log(error);
            }
        ).run();
    }
}

class TSSelectUserGroups {
    constructor(divElem) {
        this._divElem = divElem;
        this._allUserGroups = {};
        this._generateHTML();
    }

    getSelectedUserGroups() {
        var self = this;
        var selectedGroups = jQuery.extend(true, {}, this._allUserGroups);
        $.each(selectedGroups, function(ugGUID, ugData) {
            if ($.inArray(ugGUID, $("#" + self._divElem).val()) == -1) {
                delete selectedGroups[ugGUID];
            }
        });
        return selectedGroups;
    }

    _generateHTML() {
        var self = this;
        new TSGetUserGroupsRequest(
            function(data) {
                console.log('Successfully retrieved user group names from ThoughtSpot...')
                var optionsHTML = '';
                $.each(data, function(key, userGroup) {
                    if ($.inArray(userGroup.name, ['Administrator', 'System', 'All']) == -1) {
                        self._allUserGroups[userGroup.id] = userGroup.name;
                        optionsHTML += '<option value="' + userGroup.id + '">' + userGroup.name + '</option>';
                    }
                });
                $('#' + self._divElem).append(optionsHTML);
                $("#" + self._divElem).multiselect();
            },
            function(error) {
                $("#" + self._divElem).parent('.menuOption').hide();
                $('<div id="error-message" title="Failed to retrieve user groups"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>API call returned code: ' + error.status + '</p></div>').messageDialog({ dialogClass: 'error-message' });
                console.log('FAILED to retrieve usergroup names from ThoughtSpot');
                console.log(error);
            }
        ).run();
    }
}

class TSAccessSelector {

    constructor(elemSelector, selectorID, rowNo, colNo, extraClasses, onButtonClick, setValue) {
        this._elemSelector = elemSelector;
        this._selectorID = selectorID;
        this._rowNo = rowNo;
        this._colNo = colNo;
        this._extraClasses = extraClasses;
        this._onButtonClick = onButtonClick;
        this._setValue = setValue;
        this._generateHTML();
    }

    _addMainDiv() {
        var self = this;
        $(this._elemSelector).append('<div class="matrixCell"><div id="' + this._selectorID + '" class="accessSelectorGroup ROW_' + this._rowNo + ' COL_' + this._colNo + ' ' + this._extraClasses.join(' ') + '"></div></div>');
        $('#' + this._selectorID).data({
            "colNo": this._colNo,
            "rowNo": this._rowNo
        });
        $('#' + this._selectorID).click(function(event) {
            event.preventDefault();
            self._accessSelectorClick(event);
        });
    }

    _addButton(buttonClass) {
        $('#' + this._selectorID).append('<button class="accessSelector ' + buttonClass + ((this._setValue == buttonClass) ? ' Active' : ' ') + '"></button>');
        $('#' + this._selectorID + ' .' + buttonClass).data({
            "buttonValue": buttonClass
        });
    }

    _accessSelectorClick(event) {
        event.preventDefault();
        $(event.target).siblings().removeClass("Active");
        $(event.target).addClass("Active");
        this._onButtonClick(event);
    }

    _generateHTML() {
        this._addMainDiv();
        this._addButton('NO_ACCESS');
        this._addButton('READ_ONLY');
        this._addButton('MODIFY');
    }
}