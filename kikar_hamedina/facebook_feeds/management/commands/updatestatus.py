import sys
import datetime
import logging
from optparse import make_option
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

import facebook
from facebook import GraphAPIError

from facebook_feeds.models import Facebook_Status, User_Token, Facebook_Status_Attachment


FACEBOOK_API_VERSION = getattr(settings, 'FACEBOOK_API_VERSION', 'v2.1')
NUMBER_OF_TRIES_FOR_REQUEST = 3
LENGTH_OF_EMPTY_ATTACHMENT_JSON = 21


class Command(BaseCommand):
    args = '<feed_id>'
    help = 'Updates a single status'
    option_force_update = make_option('-f',
                                      '--force-update',
                                      action='store_true',
                                      dest='force-update',
                                      default=False,
                                      help='Force update of status.')

    option_force_attachment_update = make_option('-a',
                                                 '--force-attachment-update',
                                                 action='store_true',
                                                 dest='force-attachment-update',
                                                 default=False,
                                                 help='Use this flag to force updating of status attachment')

    option_list_helper = list()
    for x in BaseCommand.option_list:
        option_list_helper.append(x)
    option_list_helper.append(option_force_update)
    option_list_helper.append(option_force_attachment_update)
    option_list = tuple(option_list_helper)

    graph = facebook.GraphAPI()

    def fetch_status_object_data(self, status_id):
        """
        Receives a feed_id for a facebook
        Returns a facebook-sdk fql query, with all status objects published by the page itself.
        """
        status_data = dict()
        api_request_path = "{0}".format(status_id)
        args_for_request = {'version': FACEBOOK_API_VERSION,
                            'fields': "from, message, id, created_time, \
                             updated_time, type, link, caption, picture, description, name,\
                             status_type, story, story_tags ,object_id, properties, source, to, shares, \
                             likes.summary(true).limit(1), comments.summary(true).limit(1)"}

        try_number = 1
        while try_number <= NUMBER_OF_TRIES_FOR_REQUEST:
            try:
                status_data = self.graph.request(path=api_request_path, args=args_for_request)
                break

            except GraphAPIError:
                warning_msg = "Failed first attempt for feed #({0}) from FB API.".format(status_id)
                logger = logging.getLogger('django')
                logger.warning(warning_msg)

                if try_number == NUMBER_OF_TRIES_FOR_REQUEST:
                    error_msg = "Failed three attempts for feed #({0}) from FB API.".format(status_id)
                    logger = logging.getLogger('django.request')
                    logger.warning(error_msg)
                    status_data = {}

                try_number += 1

            # except:
            #     print 'here2'
            #     sys.exc_info()

        if not status_data:
            print 'empty dict for status returned'
        return status_data

    @staticmethod
    def insert_status_attachment(status, status_object_defaultdict):
        # print 'insert attachment'
        attachment_defaultdict = defaultdict(str, status_object_defaultdict)
        attachment = Facebook_Status_Attachment(
            status=status,
            name=attachment_defaultdict['name'],
            caption=attachment_defaultdict['caption'],
            description=attachment_defaultdict['description'],
            link=attachment_defaultdict['link'],
            facebook_object_id=attachment_defaultdict['object_id'],
            type=attachment_defaultdict['type'],
            picture=attachment_defaultdict['picture']
        )
        attachment.save()
        # add all media files related to attachment

    @staticmethod
    def update_status_attachment(attachment, status_object_defaultdict):
        # print 'update attachment'
        attachment_defaultdict = defaultdict(str, status_object_defaultdict)
        if attachment_defaultdict['link']:
            # Update relevant attachment fields
            attachment.name = attachment_defaultdict['name']
            attachment.caption = attachment_defaultdict['caption']
            attachment.description = attachment_defaultdict['description']
            attachment.link = attachment_defaultdict['link']
            attachment.facebook_object_id = attachment_defaultdict['object_id']
            attachment.type = attachment_defaultdict['type']
            attachment.picture = attachment_defaultdict['picture']
            attachment.save()
        else:
            # if has no link field - then there's no attachment, and it must be deleted
            # print 'deleting attachment'
            attachment.delete()

    def create_or_update_attachment(self, status, status_object_defaultdict):
        """
        If attachment exists, create or update all relevant fields.
        """
        # print 'create_or_update attachment'
        if status_object_defaultdict['link']:
            attachment, created = Facebook_Status_Attachment.objects.get_or_create(
                status=status)
            # print 'I have an attachment. Created now: %s; Length of data in field link: %d; \
            #     field picture: %d;  id: %s' % (created, len(status_object_defaultdict['link']),
            #                                    len(str(status_object_defaultdict['picture'])), status.status_id)
            # self.update_status_attachment(attachment, status_object_defaultdict)
        else:
            pass
            # print 'i don''t have an attachment; Link field: %s; Picture field: %s; id: %s' % (
            #     str(status_object_defaultdict['link']), str(status_object_defaultdict['picture']), status.status_id)

    def update_status_object_in_db(self, options, status_object, retrieved_status_data):
        """
        Receives a single status_object object as retrieved from facebook-sdk, and inserts the status_object
        to the db.
                """
        # Create a datetime object from int received in status_object
        current_time_of_update = datetime.datetime.strptime(retrieved_status_data['updated_time'],
                                                            '%Y-%m-%dT%H:%M:%S+0000').replace(tzinfo=timezone.utc)

        def_dict_rec = lambda: defaultdict(def_dict_rec)

        status_object_defaultdict = defaultdict(lambda: None, retrieved_status_data)
        if status_object_defaultdict['message']:
            message = status_object_defaultdict['message']
        else:
            message = ''
        if status_object_defaultdict['likes']:
            like_count = status_object_defaultdict['likes']['summary']['total_count']
        else:
            like_count = None
        if status_object_defaultdict['comments']:
            comment_count = status_object_defaultdict['comments']['summary']['total_count']
        else:
            comment_count = None
        if status_object_defaultdict['shares']:
            share_count = status_object_defaultdict['shares']['count']
        else:
            share_count = None
        if status_object_defaultdict['status_type']:
            type_of_status = status_object_defaultdict['status_type']
        else:
            type_of_status = None
        if status_object_defaultdict['story']:
            story = status_object_defaultdict['story']
        else:
            story = None
        if status_object_defaultdict['story_tags']:
            story_tags = status_object_defaultdict['story_tags']
        else:
            story_tags = None

        published = datetime.datetime.strptime(status_object_defaultdict['created_time'],
                                               '%Y-%m-%dT%H:%M:%S+0000').replace(tzinfo=timezone.utc)

        try:

            if (status_object.updated < current_time_of_update) or options['force-update']:
                # If post_id exists but of earlier update time, fields are updated.
                print 'update status_object'
                status_object.content = message
                status_object.like_count = like_count
                status_object.comment_count = comment_count
                status_object.share_count = share_count
                status_object.status_type = type_of_status  # note that fb has type AND status_type fields, here is status_type
                status_object.updated = current_time_of_update
                status_object.story = story
                status_object.story_tags = story_tags
                status_object.is_comment = status_object.set_is_comment

                # update attachment data
                self.create_or_update_attachment(status_object, status_object_defaultdict)
            elif options['force-attachment-update']:
                # force update of attachment only, regardless of time
                status_object.save()
                self.create_or_update_attachment(status_object, status_object_defaultdict)
                # If post_id exists but of equal or later time (unlikely, but may happen), disregard
                # Should be an else here for this case but as it is, just disregard
        except AttributeError:
            # If status_id is NoneType, and does not exist at all, create it from data.
            print 'create status_object'
            status_object = Facebook_Status(feed_id=retrieved_status_data['from']['id'],
                                     status_id=retrieved_status_data['id'],
                                     content=message,
                                     like_count=like_count,
                                     comment_count=comment_count,
                                     share_count=share_count,
                                     published=published,
                                     updated=current_time_of_update,
                                     status_type=type_of_status,
                                     story=story,
                                     story_tags=story_tags)

            status_object.is_comment = status_object.set_is_comment

            if status_object_defaultdict['link']:
                # There's an attachment
                status_object.save()
                self.insert_status_attachment(status_object, status_object_defaultdict)
        finally:
            # save status_object object.
            status_object.save()

    def fetch_status_data(self, status):
        """
        Returns a Dict object with Status data, by Status ID, empty Dict if not working.
        """

        status_dict = dict()
        is_skip = False
        if status.feed.feed_type == 'PP':
            try:
                # Set facebook graph access token to most up-to-date user token in db
                token = User_Token.objects.first()
                self.graph.access_token = token.token

            except AttributeError:
                # exception - trying to set an empty token (NoneType) as graph.access_token
                # Fallback: Set facebook graph access token to app access token
                self.graph.access_token = facebook.get_app_access_token(settings.FACEBOOK_APP_ID,
                                                                        settings.FACEBOOK_SECRET_KEY)
                if status.feed.requires_user_token:
                    # If the Status's Feed is set to require a user-token, and none exist in our db, the feed is skipped.
                    print 'feed %d requires user token, skipping.' % status.id
                    is_skip = True

                    # Get the data using the pre-set token

        elif status.feed.feed_type == 'UP':  # feed_type == 'UP' - User Profile
            # Set facebook graph access token to user access token
            token = User_Token.objects.filter(feeds__id=status.id).order_by('-date_of_creation').first()
            if not token:
                print 'No Token found for User Profile %s' % status
                is_skip = True
            else:
                print 'using token by user_id: %s' % token.user_id
                self.graph.access_token = token.token

        else:  # Deprecated or malfunctioning profile ('NA', 'DP')
            print 'Profile %s is of type %s, skipping.' % (status.id, status.feed_type)
            is_skip = True

        if not is_skip:
            status_dict = self.fetch_status_object_data(status.status_id)
        return status_dict

    def handle(self, *args, **options):
        """
        Executes updatestatus manage.py command.
        Receives either one status ID and updates the data for that status,
        or no status ID and therefore retrieves all Statuses and updates their data one by one.
        """

        list_of_statuses = list()
        # Case no args - fetch all feeds
        if len(args) == 0:
            list_of_statuses = [status for status in Facebook_Status.objects_no_filters.all().order_by('-published')]

        # Case arg exists - fetch status by id supplied
        elif len(args) == 1:
            status_id = args[0]
            try:
                status = Facebook_Status.objects_no_filters.get(status_id=status_id)
                list_of_statuses.append(status)

            except Facebook_Status.DoesNotExist:
                warning_msg = "Status #({0}) does not exist.".format(status_id)
                logger = logging.getLogger('django')
                logger.warning(warning_msg)
                raise CommandError('Status "%s" does not exist' % status_id)

        # Case invalid args
        else:
            raise CommandError('Please enter a valid status id')

        # Iterate over list_of_statuses
        sliced_list_of_statuses = list_of_statuses

        for i, status in enumerate(sliced_list_of_statuses):
            self.stdout.write('Working on status {0} of {1}: {2}.'.format(i+1, len(sliced_list_of_statuses), status.status_id))
            status_data = self.fetch_status_data(status)
            self.stdout.write('Successfully fetched status: {0}.'.format(status.pk))

            if status_data:
                self.update_status_object_in_db(options, status_object=status, retrieved_status_data=status_data)
                self.stdout.write('Successfully written status: {0}.'.format(status.pk))
                info_msg = "Successfully updated status: {0}.".format(status.pk)

            else:
                self.stdout.write('No data was retrieved for status: {0}.'.format(status.id))
                info_msg = "Did not successfully update status: {0}.".format(status.pk)

            logger = logging.getLogger('django')
            logger.info(info_msg)

        info_msg = "Successfully saved all statuses to db"
        logger = logging.getLogger('django')
        logger.info(info_msg)
        self.stdout.write('Successfully saved all statuses to db.')
