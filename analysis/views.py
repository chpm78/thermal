import json
import uuid

from flask import Blueprint, request, Response, url_for

import analysis.services as ans
from thermal.utils import (gather_and_enforce_request_args,
                           get_document_with_exception,
                           get_url_base,
                           item_exists)

analysis = Blueprint('analysis', __name__)


@analysis.route('/')
def index():
    '''
    Lists top level endpoints for analysis
    '''
    url_base = get_url_base()
    top_level_links = { 
        'scale_image': url_base + url_for('analysis.call_scale_image'),
        'edge_detect': url_base + url_for('analysis.call_edge_detect'),
    }
    return Response(json.dumps(top_level_links), status=200, mimetype='application/json')


@analysis.route('/scale_image')
@analysis.route('/scale_image/<image_id>')
def call_scale_image(image_id=None):
    '''
    Scales an image according to the current group settings
    '''
    result_id = uuid.uuid4()

    if not item_exists(image_id, 'picture'):  # TODO add testing for no picture id and invalid picture id
        err_msg = 'Image not found.  A valid image_id must be supplied as the last segment of the url in order to call'\
                  ' this endpoint'
        return Response(json.dumps(err_msg), status=404, mimetype='application/json')
    else:
        ans.scale_image_task.delay(img_id_in=image_id,
                                   img_id_out=result_id,
                                   group_id='current')
        resp_json = {
            'scale_image_output_image_id': str(result_id)
        }
        return Response(json.dumps(resp_json), status=202, mimetype='application/json')


@analysis.route('/edge_detect')
@analysis.route('/edge_detect/<image_id>')
def call_edge_detect(image_id=None):
    '''
    Invokes edge detection for a given image
    Accepts a GET parameter for detection threshold.  Allowable values are 'all', 'auto', 'wide' and 'tight'
    '''
    try:
        picture_dict = get_document_with_exception(image_id, document_type='picture')
        auto_id = uuid.uuid4()
        wide_id = uuid.uuid4()
        tight_id = uuid.uuid4()

        args_dict = gather_and_enforce_request_args([{'name': 'detection_threshold', 'default': 'all'}])
        if args_dict['detection_threshold'] not in ['all', 'auto', 'wide', 'tight']:
            error_msg = 'invalid detection threshold specified.  Allowable are all, auto, wide or tight'
            return Response(json.dumps(error_msg), status=409, mimetype='application/json')

        ans.edge_detect_task.delay(img_id_in=image_id,
                                   detection_threshold=args_dict['detection_threshold'],
                                   auto_id=auto_id,
                                   wide_id=wide_id,
                                   tight_id=tight_id)

        resp_json = {}
        if args_dict['detection_threshold'] in ['all', 'auto']:
            resp_json['auto_id'] = str(auto_id)
        if args_dict['detection_threshold'] in ['all', 'wide']:
            resp_json['wide_id'] = str(wide_id)
        if args_dict['detection_threshold'] in ['all', 'tight']:
            resp_json['tight_id'] = str(tight_id)

        return Response(json.dumps(resp_json), status=202, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps(e.message), status=e.status_code, mimetype='application/json')

@analysis.route('/distort_image')
@analysis.route('/distort_image/<image_id>')
def call_distort_image(image_id=None):
    '''
    Distorts an image according to the distortion pairs in the specified distortion set
    '''
    try:
        new_image_id = uuid.uuid4()
        picture_dict = get_document_with_exception(image_id, document_type='picture')
        args_dict = gather_and_enforce_request_args([{'name': 'distortion_set_id', 'required': True}])
        distortion_set_id = args_dict['distortion_set_id']
        distortion_set_dict = get_document_with_exception(distortion_set_id, document_type='distortion_set')

        # TODO call this async via distort_image_shepards_task.delay as soon as it's working
        ans.distort_image_shepards(image_id_in=image_id,
                                   image_id_out=new_image_id,
                                   distortion_set_id=distortion_set_id)

        resp_json = {
            'distorted_image_id': str(new_image_id)
        }
        return Response(json.dumps(resp_json), status=202, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps(e.message), status=e.status_code, mimetype='application/json')
