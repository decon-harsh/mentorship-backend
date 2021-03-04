from flask import request
from flask_restx import Resource, Namespace, marshal
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus

from app import messages
from app.api.resources.common import auth_header_parser
from app.api.dao.program_mentorship_relation import ProgramMentorshipRelationDAO
from app.api.dao.user import UserDAO
from app.api.models.mentorship_relation import *
from app.database.models.mentorship_relation import MentorshipRelationModel
from app.api.email_utils import send_email_program_mentorship_relation_accepted
from app.api.email_utils import send_email_new_request

program_mentorship_relation_ns = Namespace(
    "Program Mentorship Relation",
    description="Operations related to " "mentorship relations " "between users",
)
add_models_to_namespace(program_mentorship_relation_ns)

DAO = ProgramMentorshipRelationDAO()
userDAO = UserDAO()

@program_mentorship_relation_ns.route("program_mentorship_relation/send_request")
class SendRequest(Resource):
    @classmethod
    @jwt_required
    @program_mentorship_relation_ns.doc("send_request for establishing a program mentorship relation.")
    @program_mentorship_relation_ns.expect(auth_header_parser, send_program_mentorship_by_program_request_body)
    @program_mentorship_relation_ns.response(
        HTTPStatus.CREATED, f"{messages.PROGRAM_MENTORSHIP_RELATION_WAS_SENT_SUCCESSFULLY}"
    )
    @program_mentorship_relation_ns.response(
        HTTPStatus.BAD_REQUEST,
        f"{messages.MATCH_EITHER_MENTOR_OR_MENTEE}\n"
        f"{messages.MENTOR_ID_SAME_AS_MENTEE_ID}\n"
        f"{messages.END_TIME_BEFORE_PRESENT}\n"
        f"{messages.MENTOR_TIME_GREATER_THAN_MAX_TIME}\n"
        f"{messages.MENTOR_TIME_LESS_THAN_MIN_TIME}\n"
        f"{messages.MENTOR_NOT_AVAILABLE_TO_MENTOR}\n"
        f"{messages.MENTEE_NOT_AVAIL_TO_BE_MENTORED}\n"
        f"{messages.MENTOR_ALREADY_IN_A_RELATION}\n"
        f"{messages.MENTEE_ALREADY_IN_A_RELATION}\n"
        f"{messages.MENTOR_ID_FIELD_IS_MISSING}\n"
        f"{messages.MENTEE_ID_FIELD_IS_MISSING}\n"
        f"{messages.NOTES_FIELD_IS_MISSING}",
    )
    @program_mentorship_relation_ns.response(
        HTTPStatus.UNAUTHORIZED,
        f"{messages.TOKEN_HAS_EXPIRED}\n"
        f"{messages.TOKEN_IS_INVALID}\n"
        f"{messages.AUTHORISATION_TOKEN_IS_MISSING}",
    )
    @program_mentorship_relation_ns.response(
        HTTPStatus.NOT_FOUND,
        f"{messages.MENTOR_DOES_NOT_EXIST}\n" f"{messages.MENTEE_DOES_NOT_EXIST}",
    )
    def post(cls):
        """
        Creates a new mentorship relation request.

        Also, sends an email notification to the recipient about new relation request.

        Input:
        1. Header: valid access token
        2. Body: A dict containing
        - mentor_id, mentee_id: One of them must contain user ID
        - end_date: UNIX timestamp
        - notes: description of relation request

        Returns:
        Success or failure message. A mentorship request is send to the other
        person whose ID is mentioned. The relation appears at /pending endpoint.
        """

        data = request.json
        user_sender_id = get_jwt_identity()

        is_valid = SendRequest.is_valid_data(data)

        if is_valid != {}:
            return is_valid, HTTPStatus.BAD_REQUEST

        org_rep_id = data.pop("org_rep_id")
        
        if "relation_id" in data:
            relation_id = data.pop("relation_id")
            mentorship_relation = MentorshipRelationModel.find_by_id(relation_id)
            if mentorship_relation is None:
                return messages.MENTORSHIP_RELATION_DOES_NOT_EXIST, HTTPStatus.NOT_FOUND
            
            mentorship_relation_mentor_id = mentorship_relation.mentor_id 
            mentorship_relation_mentee_id = mentorship_relation.mentee_id

            if mentorship_relation.accept_date is None:
                return messages.MENTORSHIP_RELATION_NOT_IN_ACCEPT_STATE, HTTPStatus.BAD_REQUEST
            
            # request to/by mentor
            if "mentor_id" in data:
                if mentorship_relation_mentor_id == data['mentor_id']:
                    return messages.MENTORSHIP_RELATION_ALREADY_REQUESTED, HTTPStatus.BAD_REQUEST

                mentor_id = data["mentor_id"]
                mentee_id = mentorship_relation_mentee_id
                
                if mentee_id is None or mentorship_relation.action_user_id == mentee_id:
                    return messages.MENTOR_ALREADY_ACCEPTED, HTTPStatus.BAD_REQUEST

            # request to/by mentee
            if "mentee_id" in data:
                if mentorship_relation_mentee_id == data['mentee_id']:
                    return messages.MENTORSHIP_RELATION_ALREADY_REQUESTED, HTTPStatus.BAD_REQUEST
                
                mentor_id = mentorship_relation_mentor_id
                mentee_id = data["mentee_id"]

                if mentor_id is None or mentorship_relation.action_user_id == mentor_id:
                    return messages.MENTEE_ALREADY_ACCEPTED, HTTPStatus.BAD_REQUEST

        else:    
            # request to mentor
            if "mentor_id" in data:
                mentor_id = data["mentor_id"]
                mentee_id = None
                
            # request to mentee
            else:
                mentee_id = data["mentee_id"]
                mentor_id = None

            relation_id = None    
            
        response = DAO.create_program_mentorship_relation(user_sender_id, org_rep_id, mentor_id, mentee_id, relation_id, data)

        # if the mentorship relation creation failed dont send email and return
        if response[1] != HTTPStatus.CREATED.value:
            return response

        if user_sender_id == mentor_id:
            sender_role = "mentor"
            user_recipient_id = org_rep_id

        elif user_sender_id == mentee_id:
            sender_role = "mentee"
            user_recipient_id = org_rep_id

        else:
            sender_role = "Organization"
            user_recipient_id = mentor_id if mentor_id else mentee_id

        user_sender = userDAO.get_user(user_sender_id)
        user_recipient = userDAO.get_user(user_recipient_id)
        notes = data["notes"]

        send_email_new_request(user_sender, user_recipient, notes, sender_role)

        return response

    @staticmethod
    def is_valid_data(data):

        # Verify if request body has required fields
        if "org_rep_id" not in data:
            return messages.ORG_REP_ID_FIELD_IS_MISSING
        if "mentor_id" not in data and "mentee_id" not in data:
            return messages.MENTEE_OR_MENTOR_ID_FIELD_IS_MISSING
        if "mentor_id" in data and "mentee_id" in data:
            return messages.MENTEE_AND_MENTOR_ID_FIELDS_ARE_PRESENT
        if "start_date" not in data:
            return messages.START_DATE_FIELD_IS_MISSING
        if "end_date" not in data:
            return messages.END_DATE_FIELD_IS_MISSING
        if "notes" not in data:
            return messages.NOTES_FIELD_IS_MISSING

        return {}


# @program_mentorship_relation_ns.route("program_mentorship_relation/final/<int:relation_id>/send_request/")
# class SendRequest(Resource):
#     @classmethod
#     @jwt_required
#     @program_mentorship_relation_ns.doc("send_request for establishing a program mentorship relation.")
#     @program_mentorship_relation_ns.expect(auth_header_parser, send_program_mentorship_by_program_request_body)
#     @program_mentorship_relation_ns.response(
#         HTTPStatus.CREATED, f"{messages.PROGRAM_MENTORSHIP_RELATION_WAS_SENT_SUCCESSFULLY}"
#     )
#     @program_mentorship_relation_ns.response(
#         HTTPStatus.BAD_REQUEST,
#         f"{messages.MATCH_EITHER_MENTOR_OR_MENTEE}\n"
#         f"{messages.MENTOR_ID_SAME_AS_MENTEE_ID}\n"
#         f"{messages.END_TIME_BEFORE_PRESENT}\n"
#         f"{messages.MENTOR_TIME_GREATER_THAN_MAX_TIME}\n"
#         f"{messages.MENTOR_TIME_LESS_THAN_MIN_TIME}\n"
#         f"{messages.MENTOR_NOT_AVAILABLE_TO_MENTOR}\n"
#         f"{messages.MENTEE_NOT_AVAIL_TO_BE_MENTORED}\n"
#         f"{messages.MENTOR_ALREADY_IN_A_RELATION}\n"
#         f"{messages.MENTEE_ALREADY_IN_A_RELATION}\n"
#         f"{messages.MENTOR_ID_FIELD_IS_MISSING}\n"
#         f"{messages.MENTEE_ID_FIELD_IS_MISSING}\n"
#         f"{messages.NOTES_FIELD_IS_MISSING}",
#     )
#     @program_mentorship_relation_ns.response(
#         HTTPStatus.UNAUTHORIZED,
#         f"{messages.TOKEN_HAS_EXPIRED}\n"
#         f"{messages.TOKEN_IS_INVALID}\n"
#         f"{messages.AUTHORISATION_TOKEN_IS_MISSING}",
#     )
#     @program_mentorship_relation_ns.response(
#         HTTPStatus.NOT_FOUND,
#         f"{messages.MENTOR_DOES_NOT_EXIST}\n" f"{messages.MENTEE_DOES_NOT_EXIST}",
#     )
#     def post(cls):
#         """
#         Creates a new mentorship relation request.

#         Also, sends an email notification to the recipient about new relation request.

#         Input:
#         1. Header: valid access token
#         2. Body: A dict containing
#         - mentor_id, mentee_id: One of them must contain user ID
#         - end_date: UNIX timestamp
#         - notes: description of relation request

#         Returns:
#         Success or failure message. A mentorship request is send to the other
#         person whose ID is mentioned. The relation appears at /pending endpoint.
#         """

#         data = request.json
#         user_sender_id = get_jwt_identity()

#         is_valid = SendRequest.is_valid_data(data)

#         if is_valid != {}:
#             return is_valid, HTTPStatus.BAD_REQUEST

#         org_rep_id = data.pop("org_rep_id")

#         # request to mentor
#         if "mentor_id" in data:
#             mentor_id = data.pop("mentor_id")
#             mentee_id = None

#         # request to mentee
#         else:
#             mentee_id = data.pop("mentee_id")
#             mentor_id = None
        
#         response = DAO.create_program_mentorship_relation(user_sender_id, org_rep_id, mentor_id, mentee_id, None,data)

#         # if the mentorship relation creation failed dont send email and return
#         if response[1] != HTTPStatus.CREATED.value:
#             return response

#         if user_sender_id == mentor_id:
#             sender_role = "mentor"
#             user_recipient_id = org_rep_id

#         elif user_sender_id == mentee_id:
#             sender_role = "mentee"
#             user_recipient_id = org_rep_id

#         else:
#             sender_role = "Organization"
#             user_recipient_id = mentor_id if mentor_id else mentee_id

#         user_sender = userDAO.get_user(user_sender_id)
#         user_recipient = userDAO.get_user(user_recipient_id)
#         notes = data["notes"]

#         send_email_new_request(user_sender, user_recipient, notes, sender_role)

#         return response

#     @staticmethod
#     def is_valid_data(data):

#         # Verify if request body has required fields
#         if "org_rep_id" not in data:
#             return messages.ORG_REP_ID_FIELD_IS_MISSING
#         if "mentor_id" not in data and "mentee_id" not in data:
#             return messages.MENTEE_OR_MENTOR_ID_FIELD_IS_MISSING
#         if "mentor_id" in data and "mentee_id" in data:
#             return messages.MENTEE_AND_MENTOR_ID_FIELDS_ARE_PRESENT
#         if "start_date" not in data:
#             return messages.START_DATE_FIELD_IS_MISSING
#         if "end_date" not in data:
#             return messages.END_DATE_FIELD_IS_MISSING
#         if "notes" not in data:
#             return messages.NOTES_FIELD_IS_MISSING

#         return {}


@program_mentorship_relation_ns.route("program_mentorship_relation/<int:org_rep_id>/<int:request_id>/accept")
class AcceptMentorshipRelation(Resource):
    @classmethod
    @jwt_required
    @program_mentorship_relation_ns.doc("accept_mentorship_relation")
    @program_mentorship_relation_ns.expect(auth_header_parser)
    @program_mentorship_relation_ns.response(
        HTTPStatus.OK, f"{messages.MENTORSHIP_RELATION_WAS_ACCEPTED_SUCCESSFULLY}"
    )
    @program_mentorship_relation_ns.response(
        HTTPStatus.FORBIDDEN,
        f"{messages.NOT_PENDING_STATE_RELATION}\n"
        f"{messages.CANT_ACCEPT_MENTOR_REQ_SENT_BY_USER}\n"
        f"{messages.CANT_ACCEPT_UNINVOLVED_MENTOR_RELATION}\n"
        f"{messages.USER_IS_INVOLVED_IN_A_MENTORSHIP_RELATION}",
    )
    @program_mentorship_relation_ns.response(
        HTTPStatus.UNAUTHORIZED,
        f"{messages.TOKEN_HAS_EXPIRED}\n"
        f"{messages.TOKEN_IS_INVALID}\n"
        f"{messages.AUTHORISATION_TOKEN_IS_MISSING}",
    )
    @program_mentorship_relation_ns.response(
        HTTPStatus.NOT_FOUND, f"{messages.MENTORSHIP_RELATION_REQUEST_DOES_NOT_EXIST}"
    )
    def put(cls, request_id, org_rep_id):
        """
        Accept a mentorship relation.

        Input:
        1. Header: valid access token
        2. Path: ID of request which is to be accepted (request_id)

        Returns:
        Success or failure message.
        """

        # check if user id is well parsed
        # if it is an integer

        user_id = get_jwt_identity()
        response = DAO.accept_request(user_id=user_id, org_rep_id=org_rep_id , request_id=request_id,notes="okay bete")

        if response[1] == HTTPStatus.OK.value:
            send_email_program_mentorship_relation_accepted(request_id,org_rep_id)

        return response
