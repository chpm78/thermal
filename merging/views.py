import json
import uuid

from flask import Blueprint, Response, url_for
from merging.services import merge_images_task, merge_type_is_valid
from thermal.utils import cast_uuid_to_string, gather_and_enforce_request_args, get_url_base, item_exists

merging = Blueprint('merging', __name__)


@merging.route('/')
def index():
    '''
    Lists top level endpoints for the merging app
    '''
    url_base = get_url_base()
    top_level_links = {
        'merge_images': url_base + url_for('merging.call_merge_images'),
    }
    return Response(json.dumps(top_level_links), status=200, mimetype='application/json')


@merging.route('/merge_images')
def call_merge_images():
    '''
    Merges to images into a third one
    Accepts merge_type as a parameter, see here for valid merge types: http://www.effbot.org/imagingbook/imagechops.htm
    '''
    try:
        args_dict = gather_and_enforce_request_args([{'name': 'img1_id', 'required': True},
                                                     {'name': 'img2_id', 'required': True},
                                                     {'name': 'merge_type'}])
        img1_id = args_dict['img1_id']
        img2_id = args_dict['img2_id']

        if not item_exists(img1_id, 'picture'):  # TODO add testing for no picture id and invalid picture id
            err_msg = 'Source image 1 not found.  A valid id for a source image must be supplied to this endpoint as a get '\
                      'parameter named img1_id in order to call this endpoint'
            return Response(json.dumps(err_msg), status=404, mimetype='application/json')

        if not item_exists(img2_id, 'picture'):  # TODO add testing for no picture id and invalid picture id
            err_msg = 'Source image 2 not found.  A valid id for a source image must be supplied to this endpoint as a get '\
                      'parameter named img2_id in order to call this endpoint'
            return Response(json.dumps(err_msg), status=404, mimetype='application/json')

        if 'merge_type' in args_dict:
            if not merge_type_is_valid(args_dict['merge_type']):
                err_msg = 'invalid merge type specified: '+str(args_dict['merge_type'])
                return Response(json.dumps(err_msg), status=409, mimetype='application/json')
            merge_type_is_supplied = True
        else:
            merge_type_is_supplied = False

        result_id = cast_uuid_to_string(uuid.uuid4())


        if merge_type_is_supplied:
            merge_images_task.delay(
                img1_primary_id_in=img1_id,
                img1_alternate_id_in=uuid.uuid4(),
                img2_id_in=img2_id,
                img_id_out=result_id,
                group_id='current',
                merge_type=args_dict['merge_type']
            )
        else:
            merge_images_task.delay(
                img1_primary_id_in=img1_id,
                img1_alternate_id_in=uuid.uuid4(),
                img2_id_in=img2_id,
                img_id_out=result_id,
                group_id='current'
            )
        accept_json = {'result_id': result_id}
        return Response(json.dumps(accept_json), status=202, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps(e.message), status=e.status_code, mimetype='application/json')
