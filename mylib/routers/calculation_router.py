from flask_restx import Namespace, Resource, fields
from flask import request
from mylib.models.telemetry_service_model import TelemetryServiceModel

# Namespace
calc_ns = Namespace("CalculationTimeInterval", description="APIs for Calculation Interval")

# Swagger model
calc_model = calc_ns.model(
    "CalculationTimeInterval",
    {
        "CalculationTimeInterval": fields.String(
            required=False,
            description="The time interval over which the metric calculation is performed",
            pattern=r"^P(\d+D)?(T(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$"
        )
    },
)

@calc_ns.route("/<string:resource>/<string:metric_id>")
class CalculationInterval(Resource):
    @calc_ns.doc("get_calculation_time_interval")
    def get(self, resource, metric_id):
        """
        Get the CalculationTimeInterval for a given resource/metric_id
        """
        setting = TelemetryServiceModel.get_by_property(
            resource=resource,
            metric_id=metric_id,
            property="CalculationTimeInterval",
        )

        resp = {}
        if setting:
            resp["CalculationTimeInterval"] = setting.value
        return resp, 200

    @calc_ns.expect(calc_model, validate=True)
    @calc_ns.doc("patch_calculation_time_interval")
    def patch(self, resource, metric_id):
        """
        Update the CalculationTimeInterval for a given resource/metric_id
        Payload:
        {
            "CalculationTimeInterval": "PT10S"
        }
        """
        payload = request.json
        interval = payload.get("CalculationTimeInterval")

        if not interval:
            return {"error": "CalculationTimeInterval is required"}, 400

        # Save in SQLite through TelemetryServiceModel
        ok = TelemetryServiceModel.save_metric_value(
            resource=resource,
            metric_id=metric_id,
            property="CalculationTimeInterval",
            value=interval,
        )

        if not ok:
            return {"error": "Failed to update value"}, 500

        # Redfish design: only return set properties
        resp = {"CalculationTimeInterval": interval}
        return resp, 200