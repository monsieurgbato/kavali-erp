from flask import Blueprint
commercial = Blueprint('commercial', __name__)
from . import routes