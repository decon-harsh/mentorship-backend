from datetime import datetime, timedelta
from typing import Dict
from http import HTTPStatus
from app import messages
from app.database.models.mentorship_relation import MentorshipRelationModel
from app.database.models.tasks_list import TasksListModel
from app.database.models.user import UserModel
from app.utils.decorator_utils import email_verification_required
from app.utils.enum_utils import MentorshipRelationState


class ProgramMentorshipRelationDAO:
    """Data Access Object for mentorship relation functionalities.

    Provides various functions pertaining to mentorship.

    Attributes:
        MAXIMUM_MENTORSHIP_DURATION
        MINIMUM_MENTORSHIP_DURATION
    """

    def create_program_mentorship_relation(self, user_id: int, org_rep_id:int , mentor_id:int, mentee_id:int, relation_id:int, data: Dict[str, str]):
        """Creates a relationship between two users.

        Establishes the mentor-mentee relationship.

        Args:
            user_id: ID of the user initiating this request. Has to be either the mentor or the mentee.
            data: List containing the mentor_id, mentee_id, end_date_timestamp and notes.

        Returns:
            message: A message corresponding to the completed action; success if mentorship relationship is established, failure if otherwise.
        """

        # First/Initial request where mentorship relationship gets created for the first time
        if not relation_id:
            # First request to mentor by program and viceversa 
            if not mentee_id:
                action_user_id = user_id
                end_date_timestamp = data["end_date"]
                start_date_timestamp = data["start_date"]
                notes = data["notes"]

                # user_id has to match either org_representative id or mentor_id
                is_valid_user_ids = action_user_id == mentor_id or action_user_id == org_rep_id
                if not is_valid_user_ids:
                    return messages.MATCH_EITHER_MENTOR_OR_ORG_REP, HTTPStatus.BAD_REQUEST
                
                # mentor_id has to be different from org_representative id
                if mentor_id == org_rep_id:
                    return messages.MENTOR_ID_OR_MENTEE_ID_SAME_AS_ORG_REP_ID, HTTPStatus.BAD_REQUEST
                    
                try:
                    end_date_datetime = datetime.fromtimestamp(end_date_timestamp)
                except ValueError:
                    return messages.INVALID_END_DATE, HTTPStatus.BAD_REQUEST

                now_datetime = datetime.now()
                if end_date_datetime < now_datetime:
                    return messages.END_TIME_BEFORE_PRESENT, HTTPStatus.BAD_REQUEST

                # validate if mentor user exists 
                mentor_user = UserModel.find_by_id(mentor_id)
                if mentor_user is None:
                    return messages.MENTOR_DOES_NOT_EXIST, HTTPStatus.NOT_FOUND

                # validate if mentor is available to mentor
                if not mentor_user.available_to_mentor:
                    return messages.MENTOR_NOT_AVAILABLE_TO_MENTOR, HTTPStatus.BAD_REQUEST

                org_rep_user = UserModel.find_by_id(org_rep_id)
                if org_rep_user is None:
                    return messages.ORG_REP_DOES_NOT_EXIST, HTTPStatus.BAD_REQUEST


                # TODO add tests for this portion
                
                all_mentor_relations = (
                    mentor_user.mentor_relations + mentor_user.mentee_relations
                )
                for relation in all_mentor_relations:
                    if relation.state == MentorshipRelationState.ACCEPTED:
                        return messages.MENTOR_ALREADY_IN_A_RELATION, HTTPStatus.BAD_REQUEST
                
                # All validations were checked

                tasks_list = TasksListModel()
                tasks_list.save_to_db()
            
                if action_user_id == org_rep_id:
                    mentorship_relation = MentorshipRelationModel(
                        action_user_id=action_user_id,
                        mentor_user=mentor_user,
                        mentee_user=None,
                        creation_date=datetime.now().timestamp(),
                        end_date=end_date_timestamp,
                        state=MentorshipRelationState.PENDING,
                        notes=notes,
                        tasks_list=tasks_list,
                    )
                    mentorship_relation.start_date = start_date_timestamp
                
                else:
                    mentorship_relation = MentorshipRelationModel(
                        action_user_id=action_user_id,
                        mentor_user=mentor_user,
                        mentee_user=org_rep_user,
                        creation_date=datetime.now().timestamp(),
                        end_date=end_date_timestamp,
                        state=MentorshipRelationState.PENDING,
                        notes=notes,
                        tasks_list=tasks_list,
                    )
                    mentorship_relation.start_date = start_date_timestamp
                mentorship_relation.save_to_db()

            # First request to mentee by program and viceversa 
            elif not mentor_id:
                action_user_id = user_id
                end_date_timestamp = data["end_date"]
                start_date_timestamp = data["start_date"]
                notes = data["notes"]

                # user_id has to match either org_representative id or mentee_id
                is_valid_user_ids = action_user_id == mentee_id or action_user_id == org_rep_id
                if not is_valid_user_ids:
                    return messages.MATCH_EITHER_MENTOR_OR_ORG_REP, HTTPStatus.BAD_REQUEST
                
                # mentee_id has to be different from org_representative id
                if mentee_id == org_rep_id:
                    return messages.MENTOR_ID_OR_MENTEE_ID_SAME_AS_ORG_REP_ID, HTTPStatus.BAD_REQUEST
                    
                try:
                    end_date_datetime = datetime.fromtimestamp(end_date_timestamp)
                except ValueError:
                    return messages.INVALID_END_DATE, HTTPStatus.BAD_REQUEST

                now_datetime = datetime.now()
                if end_date_datetime < now_datetime:
                    return messages.END_TIME_BEFORE_PRESENT, HTTPStatus.BAD_REQUEST

                # validate if mentee user exists 
                mentee_user = UserModel.find_by_id(mentee_id)
                if mentee_user is None:
                    return messages.MENTEE_DOES_NOT_EXIST, HTTPStatus.NOT_FOUND

                # validate if mentee is available to be mentored
                if not mentee_user.need_mentoring:
                    return messages.MENTEE_NOT_AVAIL_TO_BE_MENTORED, HTTPStatus.BAD_REQUEST

                org_rep_user = UserModel.find_by_id(org_rep_id)
                if org_rep_user is None:
                    return messages.ORG_REP_DOES_NOT_EXIST, HTTPStatus.BAD_REQUEST


                # TODO add tests for this portion
                
                all_mentee_relations = (
                    mentee_user.mentor_relations + mentee_user.mentee_relations
                )
                for relation in all_mentee_relations:
                    if relation.state == MentorshipRelationState.ACCEPTED:
                        return messages.MENTEE_ALREADY_IN_A_RELATION, HTTPStatus.BAD_REQUEST

                # All validations were checked

                tasks_list = TasksListModel()
                tasks_list.save_to_db()
            
                if action_user_id == org_rep_id:
                    mentorship_relation = MentorshipRelationModel(
                        action_user_id=action_user_id,
                        mentor_user=None,
                        mentee_user=mentee_user,
                        creation_date=datetime.now().timestamp(),
                        end_date=end_date_timestamp,
                        state=MentorshipRelationState.PENDING,
                        notes=notes,
                        tasks_list=tasks_list,
                    )
                    mentorship_relation.start_date = start_date_timestamp
                
                else:
                    mentorship_relation = MentorshipRelationModel(
                        action_user_id=action_user_id,
                        mentor_user=org_rep_user,
                        mentee_user=mentee_user,
                        creation_date=datetime.now().timestamp(),
                        end_date=end_date_timestamp,
                        state=MentorshipRelationState.PENDING,
                        notes=notes,
                        tasks_list=tasks_list,
                    )
                    mentorship_relation.start_date = start_date_timestamp
                mentorship_relation.save_to_db()
            
        # Second/End requests where relationship is already present but with org_rep_user
        elif mentor_id and mentee_id and relation_id:
            if mentor_id == mentee_id:
                return messages.MENTOR_ID_SAME_AS_MENTEE_ID, HTTPStatus.BAD_REQUEST

            action_user_id = user_id
            end_date_timestamp = data["end_date"]
            start_date_timestamp = data["start_date"]
            notes = data["notes"]

            request = MentorshipRelationModel.find_by_id(relation_id)
            if request is None:
                return messages.MENTORSHIP_RELATION_DOES_NOT_EXIST, HTTPStatus.NOT_FOUND

            request_action_user_id = request.action_user_id
            request_mentor_id = request.mentor_id 
            request_mentee_id = request.mentee_id 
            request_accept_date = request.accept_date

            if request_accept_date is None:
                return messages.MENTORSHIP_RELATION_NOT_IN_ACCEPT_STATE, HTTPStatus.BAD_REQUEST

            # Program to Mentor , accepted then request to/by Mentee
            if request_mentee_id is None:
                mentee_user = UserModel.find_by_id(mentee_id)
                
                if mentee_user is None:
                    return messages.MENTEE_DOES_NOT_EXIST, HTTPStatus.NOT_FOUND

                is_valid_user_ids = action_user_id == mentee_id or action_user_id == org_rep_id
                if not is_valid_user_ids:
                    return messages.MATCH_EITHER_MENTEE_OR_ORG_REP, HTTPStatus.BAD_REQUEST
                
                if mentee_id == org_rep_id:
                    return messages.MENTOR_ID_OR_MENTEE_ID_SAME_AS_ORG_REP_ID, HTTPStatus.BAD_REQUEST
                
                # TODO add tests for this portion

                all_mentee_relations = (
                    mentee_user.mentor_relations + mentee_user.mentee_relations
                )
                for relation in all_mentee_relations:
                    if relation.state == MentorshipRelationState.ACCEPTED:
                        return messages.MENTEE_ALREADY_IN_A_RELATION, HTTPStatus.BAD_REQUEST

                # All validations were checked
                if action_user_id == org_rep_id:
                    request.action_user_id = org_rep_id

                else:
                    request.action_user_id = mentee_id
                
                request.mentee_id = mentee_id
                request.notes = notes
                request.save_to_db()

            # Program to Mentee , accepted then request to/by Mentor
            elif request_mentor_id is None:
                if not mentor_id:
                    return messages.MENTOR_ID_FIELD_IS_MISSING, HTTPStatus.BAD_REQUEST
                
                mentor_user = UserModel.find_by_id(mentor_id)
                
                if mentor_user is None:
                    return messages.MENTOR_DOES_NOT_EXIST, HTTPStatus.NOT_FOUND
                
                is_valid_user_ids = action_user_id == mentor_id or action_user_id == org_rep_id
                if not is_valid_user_ids:
                    return messages.MATCH_EITHER_MENTOR_OR_ORG_REP, HTTPStatus.BAD_REQUEST
                
                if mentor_id == org_rep_id:
                    return messages.MENTOR_ID_OR_MENTEE_ID_SAME_AS_ORG_REP_ID, HTTPStatus.BAD_REQUEST
                
                # TODO add tests for this portion
            
                all_mentor_relations = (
                    mentor_user.mentor_relations + mentor_user.mentee_relations
                )
                for relation in all_mentor_relations:
                    if relation.state == MentorshipRelationState.ACCEPTED:
                        return messages.MENTOR_ALREADY_IN_A_RELATION, HTTPStatus.BAD_REQUEST
                    
                if action_user_id == org_rep_id:
                    request.action_user_id = org_rep_id
                else:
                    request.action_user_id = mentor_id
                
                request.mentor_id = mentor_id
                request.notes = notes
                request.save_to_db()

            # Mentor/Mentee to program ,accepted then  
            else:
                # Request to/by Mentee 
                if request_mentor_id == mentor_id and request_mentee_id!=mentee_id:
                    
                    is_valid_user_ids = action_user_id == mentee_id or action_user_id == org_rep_id
                    if not is_valid_user_ids:
                        return messages.MATCH_EITHER_MENTEE_OR_ORG_REP, HTTPStatus.BAD_REQUEST
                    
                    if mentee_id == org_rep_id:
                        return messages.MENTOR_ID_OR_MENTEE_ID_SAME_AS_ORG_REP_ID, HTTPStatus.BAD_REQUEST
                    
                    if action_user_id == org_rep_id:
                        request.action_user_id = org_rep_id
                    else:
                        request.action_user_id = mentee_id
                    
                    request.mentee_id = mentee_id
                    request.notes = notes
                    request.save_to_db()
                
                # Request to/by Mentor
                elif request_mentee_id == mentee_id and request_mentor_id!=mentor_id:     
                    
                    is_valid_user_ids = action_user_id == mentor_id or action_user_id == org_rep_id
                    if not is_valid_user_ids:
                        return messages.MATCH_EITHER_MENTOR_OR_ORG_REP, HTTPStatus.BAD_REQUEST
                    
                    if mentor_id == org_rep_id:
                        return messages.MENTOR_ID_OR_MENTEE_ID_SAME_AS_ORG_REP_ID, HTTPStatus.BAD_REQUEST
                    
                    if action_user_id == org_rep_id:
                        request.action_user_id = org_rep_id
                    else:
                        request.action_user_id = mentor_id
                    
                    request.mentor_id = mentor_id
                    request.notes = notes
                    request.save_to_db()

        return messages.PROGRAM_MENTORSHIP_RELATION_WAS_SENT_SUCCESSFULLY, HTTPStatus.CREATED

    @staticmethod
    @email_verification_required
    def list_mentorship_relations(user_id=None, state=None):
        """Lists all relationships of a given user.

        Lists all relationships of a given user. Support for filtering not yet implemented.

        Args:
            user_id: ID of the user whose relationships are to be listed.

        Returns:
            message: A message corresponding to the completed action; success if all relationships of a given user are listed, failure if otherwise.
        """
        # To check if the entered 'state' is valid.
        valid_states = ["PENDING", "ACCEPTED", "REJECTED", "CANCELLED", "COMPLETED"]

        def isValidState(rel_state):
            if rel_state in valid_states:
                return True
            return False

        user = UserModel.find_by_id(user_id)
        all_relations = user.mentor_relations + user.mentee_relations

        # Filtering the list of relations on the basis of 'state'.
        if state:
            if isValidState(state):
                all_relations = list(
                    filter(lambda rel: (rel.state.name == state), all_relations)
                )
            else:
                return [], HTTPStatus.BAD_REQUEST

        # add extra field for api response
        for relation in all_relations:
            setattr(relation, "sent_by_me", relation.action_user_id == user_id)

        return all_relations, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def accept_request(user_id: int, org_rep_id:int, request_id: int, notes:str):
        """Allows a mentorship request.

        Args:
            user_id: ID of the user accepting the request.
            request_id: ID of the request to be accepted.

        Returns:
            message: A message corresponding to the completed action; success if mentorship relation request is accepted, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        request = MentorshipRelationModel.find_by_id(request_id)

        # verify if request exists
        if request is None:
            return (
                messages.MENTORSHIP_RELATION_REQUEST_DOES_NOT_EXIST,
                HTTPStatus.NOT_FOUND,
            )

        # verify if request is in pending state
        if request.state != MentorshipRelationState.PENDING:
            return messages.NOT_PENDING_STATE_RELATION, HTTPStatus.FORBIDDEN

        # verify if I'm the receiver of the request
        if request.action_user_id == user_id:
            return messages.CANT_ACCEPT_MENTOR_REQ_SENT_BY_USER, HTTPStatus.FORBIDDEN

        # verify if I'm involved in this relation
        if not (request.mentee_id == user_id or request.mentor_id == user_id):
            print(request.mentor_id)
            print(request.mentee_id)
            return messages.CANT_ACCEPT_UNINVOLVED_MENTOR_RELATION, HTTPStatus.FORBIDDEN
                
        my_requests = user.mentee_relations + user.mentor_relations

        # verify if I'm on a current relation
        for my_request in my_requests:
            if my_request.state == MentorshipRelationState.ACCEPTED:
                return (
                    messages.USER_IS_INVOLVED_IN_A_MENTORSHIP_RELATION,
                    HTTPStatus.FORBIDDEN,
                )

        mentee = request.mentee
        mentor = request.mentor
        action_user_id = request.action_user_id

        # If I am mentor : Check if the mentee isn't in any other relation already
        if mentor and mentee:
            if user_id == mentor.id:
                mentee_requests = mentee.mentee_relations + mentee.mentor_relations

                for mentee_request in mentee_requests:
                    if mentee_request.state == MentorshipRelationState.ACCEPTED:
                        return messages.MENTEE_ALREADY_IN_A_RELATION, HTTPStatus.BAD_REQUEST
            # If I am mentee : Check if the mentor isn't in any other relation already
            elif user_id == mentee.id:
                mentor_requests = mentor.mentee_relations + mentor.mentor_relations

                for mentor_request in mentor_requests:
                    if mentor_request.state == MentorshipRelationState.ACCEPTED:
                        return messages.MENTOR_ALREADY_IN_A_RELATION, HTTPStatus.BAD_REQUEST

        # mentor or mentee accepting
        if action_user_id == org_rep_id:
            request.action_user_id = user.id
            request.notes = notes
            request.accept_date = datetime.now().timestamp()
            request.save_to_db()
        else:
            request.action_user_id = org_rep_id
            request.notes = notes
            request.accept_date = datetime.now().timestamp()
            request.save_to_db()
        
        return messages.MENTORSHIP_RELATION_WAS_ACCEPTED_SUCCESSFULLY, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def reject_request(user_id: int, request_id: int):
        """Rejects a mentorship request.

        Args:
            user_id: ID of the user rejecting the request.
            request_id: ID of the request to be rejected.

        Returns:
            message: A message corresponding to the completed action; success if mentorship relation request is rejected, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        request = MentorshipRelationModel.find_by_id(request_id)

        # verify if request exists
        if request is None:
            return (
                messages.MENTORSHIP_RELATION_REQUEST_DOES_NOT_EXIST,
                HTTPStatus.NOT_FOUND,
            )

        # verify if request is in pending state
        if request.state != MentorshipRelationState.PENDING:
            return messages.NOT_PENDING_STATE_RELATION, HTTPStatus.FORBIDDEN

        # verify if I'm the receiver of the request
        if request.action_user_id == user_id:
            return messages.USER_CANT_REJECT_REQUEST_SENT_BY_USER, HTTPStatus.FORBIDDEN

        # verify if I'm involved in this relation
        if not (request.mentee_id == user_id or request.mentor_id == user_id):
            return (
                messages.CANT_REJECT_UNINVOLVED_RELATION_REQUEST,
                HTTPStatus.FORBIDDEN,
            )

        # All was checked
        request.state = MentorshipRelationState.REJECTED
        request.save_to_db()

        return messages.MENTORSHIP_RELATION_WAS_REJECTED_SUCCESSFULLY, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def cancel_relation(user_id: int, relation_id: int):
        """Allows a given user to terminate a particular relationship.

        Args:
            user_id: ID of the user terminating the relationship.
            relation_id: ID of the relationship.

        Returns:
            message: A message corresponding to the completed action; success if mentorship relation is terminated, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        request = MentorshipRelationModel.find_by_id(relation_id)

        # verify if request exists
        if request is None:
            return (
                messages.MENTORSHIP_RELATION_REQUEST_DOES_NOT_EXIST,
                HTTPStatus.NOT_FOUND,
            )

        # verify if request is in pending state
        if request.state != MentorshipRelationState.ACCEPTED:
            return messages.UNACCEPTED_STATE_RELATION, HTTPStatus.BAD_REQUEST

        # verify if I'm involved in this relation
        if not (request.mentee_id == user_id or request.mentor_id == user_id):
            return messages.CANT_CANCEL_UNINVOLVED_REQUEST, HTTPStatus.BAD_REQUEST

        # All was checked
        request.state = MentorshipRelationState.CANCELLED
        request.save_to_db()

        return messages.MENTORSHIP_RELATION_WAS_CANCELLED_SUCCESSFULLY, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def delete_request(user_id: int, request_id: int):
        """Deletes a mentorship request.

        Deletes a mentorship request if the current user was the one who created it and the request is in the pending state.

        Args:
            user_id: ID of the user that is deleting a request.
            request_id: ID of the request.

        Returns:
            message: A message corresponding to the completed action; success if mentorship relation request is deleted, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        request = MentorshipRelationModel.find_by_id(request_id)

        # verify if request exists
        if request is None:
            return (
                messages.MENTORSHIP_RELATION_REQUEST_DOES_NOT_EXIST,
                HTTPStatus.NOT_FOUND,
            )

        # verify if request is in pending state
        if request.state != MentorshipRelationState.PENDING:
            return messages.NOT_PENDING_STATE_RELATION, HTTPStatus.FORBIDDEN

        # verify if user created the mentorship request
        if request.action_user_id != user_id:
            return messages.CANT_DELETE_UNINVOLVED_REQUEST, HTTPStatus.FORBIDDEN

        # All was checked
        request.delete_from_db()

        return messages.MENTORSHIP_RELATION_WAS_DELETED_SUCCESSFULLY, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def list_past_mentorship_relations(user_id: int):
        """Lists past mentorship relation details.

        Args:
            user_id: ID of the user listing all previous relationships.

        Returns:
            message: A message corresponding to the completed action; success if past mentorship relation details are listed, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        now_timestamp = datetime.now().timestamp()
        past_relations = list(
            filter(
                lambda relation: relation.end_date < now_timestamp,
                user.mentor_relations + user.mentee_relations,
            )
        )

        for relation in past_relations:
            setattr(relation, "sent_by_me", relation.action_user_id == user_id)

        return past_relations, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def list_current_mentorship_relation(user_id: int):
        """Lists current mentorship relation details.

        Args:
            user_id: ID of the user listing all current relationships.

        Returns:
            message: A message corresponding to the completed action; success if current mentorship relation details are listed, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        all_relations = user.mentor_relations + user.mentee_relations

        for relation in all_relations:
            if relation.state == MentorshipRelationState.ACCEPTED:
                setattr(relation, "sent_by_me", relation.action_user_id == user_id)
                return relation

        return messages.NOT_IN_MENTORED_RELATION_CURRENTLY, HTTPStatus.OK

    @staticmethod
    @email_verification_required
    def list_pending_mentorship_relations(user_id: int):
        """Lists mentorship requests in pending state.

        Args:
            user_id: ID of the user listing all pending relationships.

        Returns:
            message: A message corresponding to the completed action; success if pending mentorship relation requests are listed, failure if otherwise.
        """

        user = UserModel.find_by_id(user_id)
        now_timestamp = datetime.now().timestamp()
        pending_requests = []
        all_relations = user.mentor_relations + user.mentee_relations

        for relation in all_relations:
            if (
                relation.state == MentorshipRelationState.PENDING
                and relation.end_date > now_timestamp
            ):
                setattr(relation, "sent_by_me", relation.action_user_id == user_id)
                pending_requests += [relation]

        return pending_requests, HTTPStatus.OK
