from mylib.models.account_model import AccountModel,SessionModel
from enum import Enum
from flask import request
from mylib.db.extensions import ext_engine
from werkzeug.exceptions import NotFound, MethodNotAllowed
from flask import Response, current_app
from load_env import registry_info

resource_privilege_map = registry_info["Privilege"]

class AuthStatus(Enum):
    NONE = 0          #no authentication 
    SUCCESS = 1        #successful authentication
    USERNAME_NOT_FOUND = 2  #username not found
    PASSWORD_INCORRECT = 3  #password incorrect
    ACCOUNT_DISABLE = 4
    ACCOUNT_LOCKED = 5
    AUTHORIZATION_FAILED = 6  #authorization failed, e.g. no permission to access the resource
    

def check_basic_auth(username, password):
    
    fetched_account = AccountModel.get_by_id(username)
    if fetched_account is None:
        return AuthStatus.USERNAME_NOT_FOUND
    
    if not fetched_account.enabled:
        return AuthStatus.ACCOUNT_DISABLE
    
    if fetched_account.locked:
        if fetched_account.check_if_unlocked() == False:
            return AuthStatus.ACCOUNT_LOCKED
    
    if not fetched_account.check_password(password):
        fetched_account.add_pass_err_times()
        if fetched_account.locked:
            return AuthStatus.ACCOUNT_LOCKED
        return AuthStatus.PASSWORD_INCORRECT
    # If we reach here, authentication is successful
    fetched_account.reset_pass_err_times()
    return check_authorization(username,fetched_account.role.get_priv())

def check_session_auth(token):
    fetched_session = SessionModel.get_by_token(token)
    if fetched_session is None:
        return AuthStatus.USERNAME_NOT_FOUND
    return check_authorization(fetched_session.account.user_name,fetched_session.account.role.get_priv())

resource_type_cache = {
    "/redfish/v1/AccountService": "AccountService",
    "/redfish/v1/SessionService": "SessionService",
    "/redfish/v1/SessionService/Sessions": "SessionCollection",
    "/redfish/v1/Managers/CDU/EthernetInterfaces/<string:ethernet_interfaces_id>": "EthernetInterface",
    "/redfish/v1/Managers/CDU": "Manager",
    "/redfish/v1/Managers": "ManagerCollection",
}

def get_resource_type(path: str, method='GET')->None|str:
    app = ext_engine.get_app()
    adapter = app.url_map.bind_to_environ(request.environ)
    # print(f"app.url_map: {app.url_map}")
    rule = resource_type = data = None
    try:
        endpoint, values = adapter.match(path, method=method)
        view_func = app.view_functions[endpoint]

        for r in app.url_map.iter_rules():
            if r.endpoint == endpoint and method in r.methods:
                rule = r.rule
                break
        cache_key = rule if rule else path

        # check cache
        if cache_key in resource_type_cache:
            resource_type = resource_type_cache[cache_key]
            return resource_type

        with app.test_request_context(path, method='GET'):
            response = view_func(**values)

        if isinstance(response, Response):
            if response.is_json:
                data = response.get_json()
        elif isinstance(response, dict):
            data = response

        if isinstance(data, dict) and '@odata.type' in data:
            odata_type = data.get('@odata.type')
            if odata_type and '#' in odata_type:
                parts = odata_type.split('.')
                if len(parts) > 0:
                    resource_type = parts[-1]
                    resource_type_cache[cache_key] = str(resource_type)
                    print(f" * Cached resource type for {cache_key}: {resource_type}")
        return resource_type

    except NotFound:
        print(f" * Route not found for path: {path}, method: {method}")
        return None
    except MethodNotAllowed:
        print(f" * Method not allowed for path: {path}, method: {method}")
        return None
    except Exception as e:
        print(f" * Error while checking resource type for path: {path}, method: {method} - {str(e)}")
        return None

def check_authorization(user_name, user_privileges):
    # Get path and method from the request context
    path = request.path
    method = request.method
    if not user_privileges or not isinstance(user_privileges, list):
        print("No user privileges provided or privileges are not in list format.")
        return AuthStatus.AUTHORIZATION_FAILED
    print(f" * Checking user privileges: {user_privileges}")
    if not user_privileges:
        return AuthStatus.AUTHORIZATION_FAILED
    #if not path in priv_cache:
    resource_type = get_resource_type(path, method)
    if resource_type is None:
        print(f" * Resource type not found for path: {path}, method: {method}")
        return AuthStatus.SUCCESS

    # get request body json input
    json_input = None
    if request.method in ['POST', 'PUT', 'PATCH']:
        try:
            json_input = request.get_json(silent=True)
        except Exception as e:
            print(f" * Failed to parse JSON input: {e}")
            json_input = None

    if not check_privilege(path,resource_type, method, user_name, user_privileges, json_input):
        return AuthStatus.AUTHORIZATION_FAILED
    return AuthStatus.SUCCESS

def find_ancestor_resource_type_list(path) -> list:
    """
    Find all ancestor resource types in the path by traversing up the path and calling get_resource_type.
    :param path: Redfish resource path (ex: '/redfish/v1/Managers/1')
    :return: List of ancestor resource types (from root to leaf)
    """
    resource_types = []
    current_path = path.rstrip("/")
    while current_path and current_path.startswith("/redfish/v1"):
        # Stop at /redfish/v1
        if current_path == "/redfish/v1":
            break
        # Remove trailing slash if any
        resource_type = get_resource_type(current_path)
        if resource_type:
            resource_types.append(resource_type)
        # Go up one level
        current_path = current_path.rsplit("/", 1)[0]
    resource_types.reverse()
    return resource_types

def is_subsequence(sub, seq):
    it = iter(seq)
    return all(item in it for item in sub)

def check_privilege(path, resource_type, method, user_name, usr_privilege, json_input=None):
    """
    check if user privilege meets the requirements of resource_type/method
    :param resource_type: Redfish resource type (ex: 'AccountService')
    :param method: HTTP method (ex: 'GET', 'POST')
    :param usr_privilege: user privilege list
    :param json_input: (Optional) If present, check for PropertyOverrides
    :return: True (has privilege) / False (no privilege)
    """
    global resource_privilege_map
    if not resource_type or not method or not usr_privilege:
        return False

    resource_info = resource_privilege_map.get(resource_type)
    if not resource_info:
        print(f" * No privilege definition found for resource type: {resource_type}")
        return True  # unrestricted

    op_map = resource_info.get("OperationMap")
    method = method.upper()
    property_overrides = resource_info.get("PropertyOverrides", [])
    subordinate_overrides = resource_info.get("SubordinateOverrides", {})

    # If there is no json_input， skip PropertyOverrides check
    if not (subordinate_overrides or (property_overrides and json_input and isinstance(json_input, dict))):
        return _check_op_map_privilege(op_map, method, user_name, usr_privilege, resource_type)

    # 1. If there are PropertyOverrides, we need to check them first
    overridden_fields = set()
    for override in property_overrides:
        targets = override.get("Targets", [])
        matched_fields = [field for field in json_input if field in targets]
        if not matched_fields:
            continue
        override_op_map = override.get("OperationMap")
        for field in matched_fields:
            overridden_fields.add(field)
            # User override OperationMap to check privilege
            if not _check_op_map_privilege(override_op_map, method, user_name, usr_privilege, resource_type, field):
                print(f" * Privilege check failed for override field '{field}' in resource type: {resource_type}")
                return False

    # 2. Check remaining fields in json_input that are not overridden
    if json_input:
        remaining_fields = [field for field in json_input if field not in overridden_fields]
    else:
        remaining_fields = None
    print(f" * Remaining fields after property overrides: {remaining_fields}")
    if (method == "PATCH" or method == "PUT" or method == "POST") and not remaining_fields:
        #print(" * No remaining fields to check after overrides.")
        return True

    # 3. Check SubordinateOverrides for remaining fields
    subordinate_overrides = resource_info.get("SubordinateOverrides", [])
    if subordinate_overrides:
        print(f" * Found SubordinateOverrides for resource type: {resource_type}")
        for subordinate_override in subordinate_overrides:
            if not isinstance(subordinate_override, dict):
                print(f" * SubordinateOverrides is not a dict: {subordinate_override}")
                continue
            targets = subordinate_override.get("Targets", [])
            subordinate_op_map = subordinate_override.get("OperationMap", {})
            print(f" * SubordinateOverrides targets: {targets}")
            # find ancestor resource types in path
            ancestor_resource_type_list = find_ancestor_resource_type_list(path)

            if_subsequence = is_subsequence(targets, ancestor_resource_type_list)
            print(f" * Ancestor resource types: {ancestor_resource_type_list}")
            print(f" * Targets: {targets}, if_subsequence: {if_subsequence}")

            if subordinate_op_map and if_subsequence:
                if not _check_op_map_privilege(subordinate_op_map, method, user_name, usr_privilege, resource_type, remaining_fields, ori_op_map=op_map):
                    print(f" * Privilege check failed for SubordinateOverrides fields {remaining_fields} in resource type: {resource_type}")
                    return False
    # 4. If no SubordinateOverrides or no remaining fields, check the original op_map
    else:
        if not _check_op_map_privilege(op_map, method, user_name, usr_privilege, resource_type, remaining_fields):
            print(f" * Privilege check failed for non-overridden fields {remaining_fields} in resource type: {resource_type}")
            return False

    return True

def _check_op_map_privilege(op_map, method, user_name, usr_privilege, resource_type, fields=None, ori_op_map=None):
    """
    Helper to check privilege for a given op_map and method.
    If fields is not None, just for logging purpose.
    """
    if not op_map:
        print(f" * No operation map found for resource type/method: {resource_type}/{method}")
        return True
    method_priv_list = op_map.get(method)
    if not method_priv_list or not isinstance(method_priv_list, list):
        print(f" * No privilege list found for method: {method} in resource type: {resource_type}")
        if ori_op_map:
            return _check_op_map_privilege(ori_op_map, method, usr_privilege, resource_type, fields)
        return True
    for priv_dict in method_priv_list: # or rule
        priv_list = priv_dict.get("Privilege", [])
        # all priv in priv_list must be in usr_privilege
        if all(priv in usr_privilege for priv in priv_list): # and rule
            # if priv_list equals to ['ConfigureSelf']
            if priv_list == ['ConfigureSelf'] and method == 'PATCH':
                #check the configuring name is the same as the current user name
                path = request.path
                configring_user_name = path.split("/")[-1] if path else ""
                if configring_user_name != user_name:
                    print(f" * User {user_name} does not have privilege to configure others as {configring_user_name}")
                    return False
            print(f" * User privileges {usr_privilege} meet the required privileges {priv_list}")
            print(f" * resource type: {resource_type}, method: {method}, fields: {fields}, Privilege list: {method_priv_list}")
            return True
    print(f" * User privileges {usr_privilege} do not meet the required privileges for resource type: {resource_type}, method: {method}, fields: {fields}, Privilege list: {method_priv_list}")
    return False
