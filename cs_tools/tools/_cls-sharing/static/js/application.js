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
 * Last Modified: Wednesday June 2nd 2021 2:40:49 pm
 * ==================================================================================================================================
 */
class TSTableSecurity {
    constructor(tableGUID, tableName, selectedUserGroups, targetDiv, showMessage) {
        console.log("TSTableSecurity - Creating security model for table " + tableGUID + " (" + tableName + ") and selected user groups: ");
        console.log(selectedUserGroups);
        this._tableGUID = tableGUID;
        this._tableName = tableName;
        this._userGroups = selectedUserGroups;
        this._tableAccess = {};
        this._columnAccess = {};
        this._targetDiv = targetDiv;
        this._showMessage = showMessage;
        this.refresh();
    }

    _onTablePermissionsRetrieved(data) {
        var self = this;
        console.log("TSTableSecurity - successfully retrieved table permissions");
        this._tableAccess = {}
        $.each(data[this._tableGUID].permissions, function(ugGUID, permData) {
            self._tableAccess[ugGUID] = permData.shareMode;
        });
    }

    _onColumnNamesRetrieved(data) {
        var self = this;
        console.log("TSTableSecurity - successfully retrieved column names");
        $.each(data.headers, function(index, colData) {
            self._columnAccess[colData.id] = colData.name;
        });
    }

    _onCLSRetrieved(data) {
        var self = this;
        console.log("TSTableSecurity - successfully retrieved CLS");
        var clsData = {}
        $.each(this._columnAccess, function(colGUID, columnName) {
            clsData[colGUID] = {
                "columnName": columnName,
                "permissions": {}
            }
            $.each(self._userGroups, function(ugGUID, ugData) {
                // Set the column permissions:
                // 1) first set them if they are defined.
                var setAccess = null;
                if (!jQuery.isEmptyObject(data[colGUID].permissions) && ($.inArray(ugGUID, Object.keys(data[colGUID].permissions)) != -1)) {
                    setAccess = data[colGUID].permissions[ugGUID].shareMode;
                }
                // 2) if table level permissions are set then set these (and possibly overriding CLS, like TS would do)
                if ($.inArray(ugGUID, Object.keys(self._tableAccess)) != -1) {
                    setAccess = self._tableAccess[ugGUID];
                }
                // 3) otherwise set it to no access
                if (setAccess == null) {
                    setAccess = 'NO_ACCESS';
                }
                // Set the permission in the object
                clsData[colGUID].permissions[ugGUID] = {
                    userGroupName: ugData,
                    access: setAccess
                };
                // Overlaps between CLS and table rules will be cleaned up when syncing back to TS
            });
        });
        this._columnAccess = clsData;
    }

    _onAPIError(error) {
        $('<div id="error-message" title="FAILED to execute API call"><p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 50px 0;"></span>API call returned code: ' + error.status + '</p></div>').messageDialog({ dialogClass: 'error-message' });
        console.log("TSTableSecurity - FAILED to execute API call");
        console.log(error);
    }

    _getTablePermissions() {
        new TSGetTablePermissionsRequest(
            this._tableGUID,
            this._onTablePermissionsRetrieved.bind(this),
            this._onAPIError.bind(this)
        ).run();
    }

    _getTableColumns() {
        console.log('Getting column names for security for table:' + this._tableGUID);
        new TSGetColumnsRequest(
            this._tableGUID,
            this._onColumnNamesRetrieved.bind(this),
            this._onAPIError.bind(this)
        ).run();
    }

    _getCLS() {
        new TSGetColumnPermissionsRequest(
            Object.keys(this._columnAccess),
            this._onCLSRetrieved.bind(this),
            this._onAPIError.bind(this)
        ).run();
    }

    _accessSelectorClick(event) {
        event.preventDefault();
        $(event.target).siblings().removeClass("Active");
        $(event.target).addClass("Active");
    }

    _generateHTMLInterface() {
        var self = this;
        var rowNo = 0;
        var colNo = 0;
        $(this._targetDiv).empty();

        //------------------------------
        // Add user group headers
        //------------------------------
        $(this._targetDiv).append('<div class="matrixRow userGroupHeaders"></div>');
        $(this._targetDiv + ' .userGroupHeaders').append('<div class="matrixCell"></div>');
        $.each(this._userGroups, function(ugGUID, userGroupName) {
            $(self._targetDiv + ' .userGroupHeaders').append('<div class="matrixCell">' + userGroupName + '</div>');
        });

        //------------------------------
        // Add the 'select all' headers
        //------------------------------
        $(this._targetDiv).append('<div class="matrixRow selectAllHeaders"></div>');
        $(this._targetDiv + ' .selectAllHeaders').append('<div class="matrixCell">Apply to all</div>');
        $.each(this._userGroups, function(ugGUID, userGroupName) {
            colNo++
            new TSAccessSelector(self._targetDiv + ' .selectAllHeaders', 'checkAll_' + ugGUID, rowNo, colNo, [], function(event) {
                jQuery('.clsSelectors.COL_' + $('#checkAll_' + ugGUID).data("colNo")).each(function() {
                    $(this).children('.' + $(event.target).data('buttonValue')).trigger('click');
                });
            }, null);
        });

        //------------------------------
        // Add the cls entries
        //------------------------------
        $.each(this._columnAccess, function(colGUID, clsData) {
            rowNo++;
            colNo = 0;
            $(self._targetDiv).append('<div class="matrixRow permissionRows ROW_' + rowNo + '"><div class="matrixCell">' + clsData.columnName + '</div></div>');
            $.each(clsData.permissions, function(ugGUID, userGroupName) {
                colNo++;
                new TSAccessSelector(self._targetDiv + ' .permissionRows.ROW_' + rowNo, colGUID + '_' + ugGUID, rowNo, colNo, ['clsSelectors'], function(event) {
                    event.preventDefault();
                    self.setAccess(colGUID, ugGUID, $(event.target).data('buttonValue'));
                }, self.getAccess(colGUID, ugGUID));
            });
        });

        $('#progressLoader').loadingOverlay('remove');
        //------------------------------
        // Add the update button
        //------------------------------
        $(self._targetDiv).append('<div id="updateSecurity">Update Security</div>');
        $('#updateSecurity').click(function() {
            $('#progressLoader').loadingOverlay({
                loadingText: 'Applying security...'
            });
            // self._generateHTMLInterface();
            self._updateTSSecurity();
        });
    }

    _optimizeMatrix() {
        var self = this;
        var colNo = 1;

        // Clear all table access rules
        self._tableAccess = {};
        // Set the new table access rules
        $.each(this._userGroups, function(ugGUID, ugName) {
            $.each(['NO_ACCESS', 'READ_ONLY', 'MODIFY'], function(index, accessType) {
                if ($('.clsSelectors.COL_' + colNo + ' .accessSelector.' + accessType + '.Active').length == $('.clsSelectors.COL_' + colNo).length) {
                    console.log('Table Access rule for usergroup ' + ugName + ' : ' + accessType);
                    self._tableAccess[ugGUID] = accessType;
                    // Remove all cls rules for these columns
                    $.each(self._columnAccess, function(colGUID, colData) {
                        delete colData.permissions[ugGUID];
                    });
                    return false;
                }
            });
            if ($.inArray(ugGUID, Object.keys(self._tableAccess)) == -1) {
                console.log('For user group ' + ugName + ' CLS needs to be applied');
                // remove table access rule
                delete self._tableAccess[ugGUID];
            }
            colNo++;
        });

        // Create unique key to reduce API
        $.each(self._columnAccess, function(colGUID, colData) {
            var cMap = "";
            $.each(colData.permissions, function(ugGUID, accessData) {
                cMap = cMap + '|' + accessData.access;
            });
            colData['cMap'] = cMap;
        });

    }
    _updateTSSecurity() {
        var self = this;
        this._optimizeMatrix();

        // Now update the TS Security
        var clearPermissions = {
            "permissions": {}
        }

        // Build clearing permissions list
        console.log('Building clearing permissions list');
        $.each(this._userGroups, function(ugGUID, ugName) {
            clearPermissions.permissions[ugGUID] = { "shareMode": "NO_ACCESS" };
        });

        // 1) clear all existing security
        // 1a) Clear all table level rules
        console.log('Clearing table permissions');
        new TSSetTablePermissionRequest(
            this._tableGUID,
            clearPermissions,
            function(data) {
                console.log('Successfully cleared table permissions...');
            },
            function(error) {
                console.log('FAILED to clear table permissions.');
                console.log(error);
            }).run();

        // 1b) Clear all CLS rules
        console.log('Clearing all CLS rules');
        new TSSetColumnPermissionRequest(
            Object.keys(this._columnAccess),
            clearPermissions,
            function(data) {
                console.log('Successfully clear column permissions...');
            },
            function(data) {
                console.log('FAILED to clear column permissions');
            }
        ).run();

        // 2) Apply table level rules
        var ugAccess = {
            "permissions": {}
        };
        $.each(this._tableAccess, function(ugGUID, permission) {
            ugAccess.permissions[ugGUID] = {
                "shareMode": permission
            }
        })
        console.log('Setting table permissions:');
        if (!jQuery.isEmptyObject(ugAccess.permissions)) {
            new TSSetTablePermissionRequest(
                this._tableGUID,
                ugAccess,
                function(data) {
                    console.log('Successfully set table permissions...');
                },
                function(error) {
                    console.log('FAILED to set table permissions.');
                    console.log(error);
                }).run();
        }
        // 3) Apply CLS rules
        console.log('Setting CLS permissions');

        var uniqueSets = [];
        $.each(self._columnAccess, function(colGUID, colData) {
            if (($.inArray(colData.cMap, uniqueSets) == -1) && (colData.cMap != '')) {
                uniqueSets.push(colData.cMap);
            }
        });

        var execCount = 0;
        $.each(uniqueSets, function(index, setName) {
            var colArray = [];
            var permissions = {}
            $.each(self._columnAccess, function(colGUID, colData) {
                if (colData.cMap == setName) {
                    colArray.push(colGUID);

                    $.each(colData.permissions, function(ugGUID, ugData) {
                        permissions[ugGUID] = {
                            shareMode: ugData.access
                        }
                    })
                }
            });

            execCount++;
            new TSSetColumnPermissionRequest(
                colArray, {
                    "permissions": permissions
                },
                function(data) {
                    console.log('Completed CLS Request No ' + execCount);
                    console.log('Successfully set column permissions...');
                },
                function(data) {
                    console.log('Failed CLS Request No ' + execCount);
                    console.log('FAILED to set column permissions');
                }
            ).run();

        });

        // Small tables are quite quick, so at least show the message for 2 seconds
        setTimeout(function() {
            $('#progressLoader').loadingOverlay('remove');
            self._showMessage(true, 'Security has been updated!', 'All security has been successfully updated.');
        }, 2000);

    }

    getAccess(colGUID, ugGUID) {
        var access = this._columnAccess[colGUID].permissions[ugGUID].access;
        return (access == null) ? 'NO_ACCESS' : access;
    }

    setAccess(colGUID, ugGUID, access) {
        this._columnAccess[colGUID].permissions[ugGUID].access = access;
    }

    refresh() {
        this._tableAccess = {};
        this._getTablePermissions();
        this._getTableColumns();
        this._getCLS();
        if (this._targetDiv != "") {
            this._generateHTMLInterface();
        }
    }
}

class Application {

    constructor() {
        this._tsTableSecurity = null;
        this._userGroupSelector = new TSSelectUserGroups("selUserGroups");
        this._tableSelector = new TSSelectTable("tableName");
    }

    _getPermissions(event) {
        $('#progressLoader').loadingOverlay({
            loadingText: 'Loading security...'
        });

        this._tsTableSecurity = new TSTableSecurity(
            $('#tableName').val(),
            $("#tableName option:selected").text(),
            this._userGroupSelector.getSelectedUserGroups(),
            '#securityMatrix',
            this._showMessage
        );

    }
    _initialiseInterface() {
        console.log('Initialising interface...');
        var self = this;
        $("#getPermissions").click(this._getPermissions.bind(this));
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

    init() {
        console.log('Initialising application....')
        this._initialiseInterface();
    }

}


$(document).ready(function() {
    console.log('DOM ready...');
    const app = new Application().init()
});