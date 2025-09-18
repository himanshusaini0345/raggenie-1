from typing import Any
from loguru import logger

from app.utils.sb_decoder import decode_data
from datetime import datetime
from loguru import logger
from decimal import Decimal


class Formatter:
    def format(self, data: Any,input) -> (dict):
        """
        Main entry point for formatting the data based on the input parameters.
        Handles different formatting strategies based on operation kind.

        :param data: The data to format.
        :param input_params: Dictionary containing operation and formatting details.
        :return: A dictionary containing the formatted response.
        """
        response = {}
        self.main_entity = input.get("main_entity")
        if input.get("operation_kind", ""):
            self.kind = input.get("operation_kind", "").lower()
        else:
            self.kind = ""
        self.general_message = input.get("general_message")
        self.empty_message = input.get("empty_message")
        if data is not None:
            data = self.preprocess_data(data)
            

        logger.info("Formatting output using inference for mysql")

        if self.kind  == "list":
            response = self.basic_formatter(data, input)
        elif self.kind == "aggregation":
            response = self.aggregation_formatter(data, input)
        else:
            response["data"] = data
            response["kind"] = "list"


        response.update({
            "main_entity": self.main_entity,
            "main_format": self.kind,
            "role": "assistant",
            "content": self.general_message,
        })

        return response

    def basic_formatter(self, data: Any, input:Any) -> dict :
        """
        Formats data as a list, handling cases for none, single, and multiple entries.

        :param data: The data to format.
        :return: A dictionary containing the formatted list response.
        """
        logger.info("Formatting data as a list")

        if data is None:
            response = {"data": [], "kind": "none"}
        elif len(data) == 1:
            response = {"data": data, "kind": "single"}
        else:
            response = {"data": data, "kind": "list"}

        return response


    def aggregation_formatter(self, data:Any, input:Any) -> dict :
        """
        Formats data for aggregation visualisation, supporting table and chart formats.

        :param data: The data to format.
        :param visualisation: Dictionary containing visualisation details (e.g., x-axis, y-axis, chart type).
        :return: A dictionary containing the formatted aggregation response.
        """

        logger.info("Formatting data as aggregation")

        visualisation = input.get("visualisation", {})
        response = {}


        if data is None or len(data) == 0:
            response = {"data": [], "kind": "none"}
        elif len(data) == 1:
            response = {"data": data, "kind": "table"}
        else:
            value_fields = visualisation.get("y-axis", [])
            key_fields = visualisation.get("x-axis", [])
            title = visualisation.get("title", "")

            visualisaton_kind = visualisation["type"].replace(" ", "_") if visualisation["type"] is not None else "table"

            if visualisaton_kind.lower() in ["bar_chart", "line_chart", "pie_chart"] and len(value_fields) > 0 and len(key_fields) > 0:
                response["kind"] = visualisaton_kind
                response["data"] = data
                response["x"] = key_fields
                response["y"] = value_fields
                response["title"] = title
            else:
                response = {"kind": "table", "data": data}

        return response

    def preprocess_data(self, data):
        logger.info(f"data:{data}")
        for entry in data:
            for key, value in entry.items():
                if isinstance(value, str):
                    decoded_value = decode_data(value)
                    if decoded_value != "":
                        entry[key] = decoded_value
                if isinstance(value, datetime):
                    entry[key] = value.isoformat()  # Convert datetime to ISO 8601 string
                elif isinstance(value, Decimal):
                    entry[key] = float(value)  # Convert Decimal to float

        return data


