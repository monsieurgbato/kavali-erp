from flask import Blueprint
logistique = Blueprint('logistique', __name__)
from . import routes