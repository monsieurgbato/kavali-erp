from flask import Blueprint
fleet = Blueprint('fleet', __name__)
from . import routes