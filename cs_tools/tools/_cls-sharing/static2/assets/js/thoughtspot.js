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
 * Last Modified: Wednesday June 2nd 2021 2:44:19 pm
 * ==================================================================================================================================
 */
SHARED_INSTANCE = "https://13.56.2.129";
HARRI = "https://harri.thoughtspot.cloud";
SANDBOX = "https://18.185.153.97";

TS_URL = SHARED_INSTANCE;


class TSAPIGET {
    constructor(onSuccess, onFailure) {
        this._onSuccess = onSuccess;
        this._onFailure = onFailure;
        this._requestType = "GET";
        this._requestDataType = "JSON";
        this._requestURL = "";
    }

    run() {
        var self = this;
        console.log('Executing GET API CALL: ' + this._requestURL);
        $.ajax({
                url: this._requestURL,
                type: this._requestType,
                dataType: this._requestDataType,
                xhrFields: {
                    withCredentials: true,
                },
                async: false
            })
            .done(function(data) {
                self._onSuccess(data);
            })
            .fail(function(error) {
                console.log("API Call Failed");
                self._onFailure(error);
            });
    }

}

class TSGetTablesRequest extends TSAPIGET {

    constructor(onSuccess, onFailure) {
        super(onSuccess, onFailure);
        this._requestURL = TS_URL + '/callosum/v1/tspublic/v1/metadata/listobjectheaders?type=LOGICAL_TABLE&subtypes=%5B%22ONE_TO_ONE_LOGICAL%22%5D&category=ALL&sort=DEFAULT&offset=-1';
    }
}

class TSGetUserGroupsRequest extends TSAPIGET {

    constructor(onSuccess, onFailure) {
        super(onSuccess, onFailure);
        this._requestURL = TS_URL + '/callosum/v1/tspublic/v1/metadata/listobjectheaders?type=USER_GROUP&category=ALL&sort=DEFAULT&offset=-1&auto_created=false'
    }
}

class TSGetColumnsRequest extends TSAPIGET {

    constructor(tableId, onSuccess, onFailure) {
        super(onSuccess, onFailure);
        this._requestURL = TS_URL + '/callosum/v1/metadata/listcolumns/' + tableId + '?showhidden=false';
    }
}


class TSAPIPost {
    constructor(onSuccess, onFailure) {
        this._onSuccess = onSuccess;
        this._onFailure = onFailure;
        this._requestURL = "";
        this._objectType = "";
        this._requestType = "POST";
        this._requestDataType = "JSON";
        this._data = {};
    }

    run() {
        console.log('Executing POST API CALL: ' + this._requestURL);
        var self = this;
        $.ajax({
                url: this._requestURL,
                data: this._data,
                type: this._requestType,
                dataType: this._requestDataType,
                xhrFields: {
                    withCredentials: true,
                },
                async: false
            })
            .done(function(data) {
                self._onSuccess(data);
            })
            .fail(function(error) {
                self._onFailure(error);
            });
    }

}

class TSGetObjectPermissionsRequest extends TSAPIPost {
    constructor(onSuccess, onFailure) {
        super(onSuccess, onFailure);
        this._requestURL = TS_URL + '/callosum/v1/security/definedpermission';
        this._data = {}
    }
}
class TSGetTablePermissionsRequest extends TSGetObjectPermissionsRequest {

    constructor(tableID, onSuccess, onFailure) {
        super(onSuccess, onFailure);

        this._data = {
            type: "LOGICAL_TABLE",
            id: JSON.stringify([tableID])
        }
    }
}

class TSGetColumnPermissionsRequest extends TSGetObjectPermissionsRequest {

    constructor(columnIDs, onSuccess, onFailure) {
        super(onSuccess, onFailure);
        this._data = {
            type: "LOGICAL_COLUMN",
            id: JSON.stringify(columnIDs)
        }
    }
}


class TSSetPermissionRequest extends TSAPIPost {

    constructor(objectIDs, objectPermissions, onSuccess, onFailure) {
        super(onSuccess, onFailure);

        this._requestURL = TS_URL + '/callosum/v1/security/share'
        this._data = {
            type: "",
            id: JSON.stringify(objectIDs),
            permission: JSON.stringify(objectPermissions)
        };
    }
}


class TSSetColumnPermissionRequest extends TSSetPermissionRequest {
    constructor(columnIDs, columnPermissions, onSuccess, onFailure) {
        super(columnIDs, columnPermissions, onSuccess, onFailure);
        this._data.type = "LOGICAL_COLUMN";
    }
}

class TSSetTablePermissionRequest extends TSSetPermissionRequest {
    constructor(tableID, tablePermissions, onSuccess, onFailure) {
        super([tableID], tablePermissions, onSuccess, onFailure);
        this._data.type = "LOGICAL_TABLE";
    }
}
