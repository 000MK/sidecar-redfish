import json
from flask import request,jsonify, Response
from flask import make_response
from flask_restx import Namespace, Resource, fields
from mylib.services.rf_registries import RfRegistries
from mylib.utils.rf_error import *

Registries_ns = Namespace('', description='Registries')

#================================================
# Registries
#================================================
@Registries_ns.route("/Registries")
class RegistriesService(Resource):
    def get(self):
        registries = RfRegistries.fetch_registries()
        resp = Response(json.dumps(registries), status=200, content_type="application/json")
        resp.headers['Allow'] = 'GET'
        return resp
    
@Registries_ns.route("/Registries/Base")
class RegistryBase(Resource):
    def get(self):
        register_base = RfRegistries.fetch_registry_base()
        resp = Response(json.dumps(register_base), status=200, content_type="application/json")
        resp.headers['Allow'] = 'GET'
        return resp
    
#Base.v1_21_0
@Registries_ns.route("/Registries/Base/Base.v1_21_0")
class RegistryBaseV1_21_0(Resource):
    def get(self):
        register_base = RfRegistries.fetch_registry_base_v1_21_0()
        resp = Response(json.dumps(register_base), status=200, content_type="application/json")
        resp.headers['Allow'] = 'GET'
        return resp