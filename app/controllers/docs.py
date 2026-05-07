from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from ..docs.openapi import build_openapi_spec
from ..docs.postman import build_postman_collection, build_postman_environment


docs_bp = Blueprint("docs", __name__)


@docs_bp.get("/swagger")
@docs_bp.get("/docs")
def swagger_ui():
    return render_template("swagger.html")


@docs_bp.get("/api/openapi.json")
def openapi_json():
    return jsonify(build_openapi_spec())


@docs_bp.get("/api/postman.json")
def postman_json():
    return jsonify(build_postman_collection())


@docs_bp.get("/api/postman-environment.json")
def postman_environment_json():
    return jsonify(build_postman_environment())
