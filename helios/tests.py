"""
Unit Tests for Helios
"""

import datetime
import logging
import re
import uuid
from urllib.parse import urlencode

import django_webtest
from django.conf import settings
from django.core import mail
from django.core.files import File
from django.test import TestCase
from django.utils.html import escape as html_escape

import helios.datatypes as datatypes
import helios.models as models
import helios.utils as utils
import helios.views as views
from helios import tasks
from helios_auth import models as auth_models


class ElectionModelTests(TestCase):
    fixtures = ['users.json']
    allow_database_queries = True

    def create_election(self):
        return models.Election.get_or_create(
            short_name='demo',
            name='Demo Election',
            description='Demo Election Description',
            admin=self.user)

    def setup_questions(self):
        QUESTIONS = [{"answer_urls": [None, None, None], "answers": ["a", "b", "c"], "choice_type": "approval", "max": 1, "min": 0, "question": "w?", "result_type": "absolute", "short_name": "w?", "tally_type": "homomorphic"}]
        self.election.questions = QUESTIONS

    def setup_trustee(self):
        self.election.generate_trustee(views.ELGAMAL_PARAMS)

    def setup_openreg(self):
        self.election.openreg=True
        self.election.save()
    
    def setUp(self):
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')
        self.fb_user = auth_models.User.objects.filter(user_type='facebook')[0]
        self.election, self.created_p = self.create_election()

    def test_create_election(self):
        # election should be created
        self.assertTrue(self.created_p)

        # should have a creation time
        self.assertNotEqual(self.election.created_at, None)
        self.assertTrue(self.election.created_at < datetime.datetime.utcnow())

    def test_find_election(self):
        election = models.Election.get_by_user_as_admin(self.user)[0]
        self.assertEqual(self.election, election)

        election = models.Election.get_by_uuid(self.election.uuid)
        self.assertEqual(self.election, election)

        election = models.Election.get_by_short_name(self.election.short_name)
        self.assertEqual(self.election, election)
        
    def test_setup_trustee(self):
        self.setup_trustee()
        self.assertEqual(self.election.num_trustees, 1)

    def test_add_voters_file(self):
        election = self.election

        FILE = "helios/fixtures/voter-file.csv"
        with open(FILE, 'r', encoding='utf-8') as f:
            vf = models.VoterFile.objects.create(election = election, voter_file = File(f, "voter_file.css"))
            vf.process()

        # make sure that we stripped things correctly
        voter = election.voter_set.get(voter_login_id = 'benadida5')
        self.assertEqual(voter.voter_email, 'ben5@adida.net')
        self.assertEqual(voter.voter_name, 'Ben5 Adida')

    def test_check_issues_before_freeze(self):
        # should be three issues: no trustees, and no questions, and no voters
        issues = self.election.issues_before_freeze
        self.assertEqual(len(issues), 3)

        self.setup_questions()

        # should be two issues: no trustees, and no voters
        issues = self.election.issues_before_freeze
        self.assertEqual(len(issues), 2)

        self.election.questions = None

        self.setup_trustee()

        # should be two issues: no questions, and no voters
        issues = self.election.issues_before_freeze
        self.assertEqual(len(issues), 2)
        
        self.setup_questions()

        # move to open reg
        self.setup_openreg()

        issues = self.election.issues_before_freeze
        self.assertEqual(len(issues), 0)
        
    def test_helios_trustee(self):
        self.election.generate_trustee(views.ELGAMAL_PARAMS)

        self.assertTrue(self.election.has_helios_trustee())

        trustee = self.election.get_helios_trustee()
        self.assertNotEqual(trustee, None)

    def test_log(self):
        LOGS = ["testing 1", "testing 2", "testing 3"]

        for l in LOGS:
            self.election.append_log(l)

        pulled_logs = [l.log for l in self.election.get_log().all()]
        pulled_logs.reverse()

        self.assertEqual(LOGS,pulled_logs)

    def test_eligibility(self):
        self.election.eligibility = [{'auth_system': self.user.user_type}]

        # without openreg, this should be false
        self.assertFalse(self.election.user_eligible_p(self.user))
        
        # what about after saving?
        self.election.save()
        e = models.Election.objects.get(uuid = self.election.uuid)
        self.assertEqual(e.eligibility, [{'auth_system': self.user.user_type}])

        self.election.openreg = True

        # without openreg, and now true
        self.assertTrue(self.election.user_eligible_p(self.user))

        # try getting pretty eligibility, make sure it doesn't throw an exception
        assert self.user.user_type in self.election.pretty_eligibility

    def test_facebook_eligibility(self):
        self.election.eligibility = [{'auth_system': 'facebook', 'constraint':[{'group': {'id': '123', 'name':'Fake Group'}}]}]

        import settings
        fb_enabled = 'facebook' in settings.AUTH_ENABLED_SYSTEMS
        if not fb_enabled:
            logging.error("'facebook' not enabled for auth, cannot its constraints.")
            self.assertFalse(self.election.user_eligible_p(self.fb_user))
            return

        # without openreg, this should be false
        self.assertFalse(self.election.user_eligible_p(self.fb_user))
        
        self.election.openreg = True

        # fake out the facebook constraint checking, since
        # our access_token is obviously wrong
        from helios_auth.auth_systems import facebook

        def fake_check_constraint(constraint, user):
            return constraint == {'group': {'id': '123', 'name':'Fake Group'}} and user == self.fb_user                
        facebook.check_constraint = fake_check_constraint

        self.assertTrue(self.election.user_eligible_p(self.fb_user))

        # also check that eligibility_category_id does the right thing
        self.assertEqual(self.election.eligibility_category_id('facebook'), '123')

    def test_freeze(self):
        # freezing without trustees and questions, no good
        def try_freeze():
            self.election.freeze()
        self.assertRaises(Exception, try_freeze)
        
        self.setup_questions()
        self.setup_trustee()
        self.setup_openreg()

        # this time it should work
        try_freeze()
        
        # make sure it logged something
        self.assertTrue(len(self.election.get_log().all()) > 0)

    def test_archive(self):
        self.election.archived_at = datetime.datetime.utcnow()
        self.assertTrue(self.election.is_archived)

        self.election.archived_at = None
        self.assertFalse(self.election.is_archived)

    def test_voter_registration(self):
        # before adding a voter
        voters = models.Voter.get_by_election(self.election)
        self.assertEqual(0, len(voters))

        # make sure no voter yet
        voter = models.Voter.get_by_election_and_user(self.election, self.user)
        self.assertIsNone(voter)

        # make sure no voter at all across all elections
        voters = models.Voter.get_by_user(self.user)
        self.assertEqual(0, len(voters))

        # register the voter
        voter = models.Voter.register_user_in_election(self.user, self.election)
        
        # make sure voter is there now
        voter_2 = models.Voter.get_by_election_and_user(self.election, self.user)

        self.assertIsNotNone(voter)
        self.assertIsNotNone(voter_2)
        self.assertEqual(voter, voter_2)

        # make sure voter is there in this call too
        voters = models.Voter.get_by_user(self.user)
        self.assertEqual(1, len(voters))
        self.assertEqual(voter, voters[0])

        voter_2 = models.Voter.get_by_election_and_uuid(self.election, voter.uuid)
        self.assertEqual(voter, voter_2)

        self.assertEqual(voter.user, self.user)



class VoterModelTests(TestCase):
    fixtures = ['users.json', 'election.json']
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.get(short_name='test')

    def test_create_password_voter(self):
        v = models.Voter(uuid = str(uuid.uuid1()), election = self.election, voter_login_id = 'voter_test_1', voter_name = 'Voter Test 1', voter_email='foobar@acme.com')

        v.generate_password()

        v.save()
        
        # password has been generated!
        self.assertFalse(v.voter_password is None)

        # can't generate passwords twice
        self.assertRaises(Exception, lambda: v.generate_password())
        
        # check that you can get at the voter user structure
        self.assertEqual(v.get_user().user_id, v.voter_email)


class CastVoteModelTests(TestCase):
    fixtures = ['users.json', 'election.json']
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.get(short_name='test')
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

        # register the voter
        self.voter = models.Voter.register_user_in_election(self.user, self.election)

    def test_cast_vote(self):
        pass

class DatatypeTests(TestCase):
    fixtures = ['users.json', 'election.json']
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.election.generate_trustee(views.ELGAMAL_PARAMS)

    def test_instantiate(self):
        ld_obj = datatypes.LDObject.instantiate(self.election.get_helios_trustee(), '2011/01/Trustee')
        foo = ld_obj.serialize()

    def test_from_dict(self):
        ld_obj = datatypes.LDObject.fromDict({
                'y' : '1234',
                'p' : '23434',
                'g' : '2343243242',
                'q' : '2343242343434'}, type_hint = 'pkc/elgamal/PublicKey')

    def test_dictobject_from_dict(self):
        original_dict = {
            'A' : '35423432',
            'B' : '234324243'}
        ld_obj = datatypes.LDObject.fromDict(original_dict, type_hint = 'legacy/EGZKProofCommitment')

        self.assertEqual(original_dict, ld_obj.toDict())
        
        
        

##
## Black box tests
##

class DataFormatBlackboxTests(object):
    def setUp(self):
        self.election = models.Election.objects.all()[0]

    def assertEqualsToFile(self, response, file_path):
        with open(file_path) as expected:
            self.assertEqual(response.content, expected.read().encode('utf-8'))

    def test_election(self):
        response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_ELECTION_FILE)

    def test_election_metadata(self):
        response = self.client.get("/helios/elections/%s/meta" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_ELECTION_METADATA_FILE)

    def test_voters_list(self):
        response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_VOTERS_FILE)

    def test_trustees_list(self):
        response = self.client.get("/helios/elections/%s/trustees/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_TRUSTEES_FILE)

    def test_ballots_list(self):
        response = self.client.get("/helios/elections/%s/ballots/" % self.election.uuid, follow=False)
        self.assertEqualsToFile(response, self.EXPECTED_BALLOTS_FILE)

## now we have a set of fixtures and expected results for various formats
## note how TestCase is used as a "mixin" here, so that the generic DataFormatBlackboxTests
## does not register as a set of test cases to run, but each concrete data format does.

class LegacyElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
    fixtures = ['legacy-data.json']
    allow_database_queries = True
    EXPECTED_ELECTION_FILE = 'helios/fixtures/legacy-election-expected.json'
    EXPECTED_ELECTION_METADATA_FILE = 'helios/fixtures/legacy-election-metadata-expected.json'
    EXPECTED_VOTERS_FILE = 'helios/fixtures/legacy-election-voters-expected.json'
    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/legacy-trustees-expected.json'
    EXPECTED_BALLOTS_FILE = 'helios/fixtures/legacy-ballots-expected.json'

#class V3_1_ElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
#    fixtures = ['v3.1-data.json']
#    EXPECTED_ELECTION_FILE = 'helios/fixtures/v3.1-election-expected.json'
#    EXPECTED_VOTERS_FILE = 'helios/fixtures/v3.1-election-voters-expected.json'
#    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/v3.1-trustees-expected.json'
#    EXPECTED_BALLOTS_FILE = 'helios/fixtures/v3.1-ballots-expected.json'

class WebTest(django_webtest.WebTest):
    def assertStatusCode(self, response, status_code):
        actual_code = response.status_code if hasattr(response, 'status_code') else response.status_int
        if isinstance(status_code, (list, tuple)):
            assert actual_code in status_code, "%s instad of %s" % (actual_code, status_code)
        else:
            assert actual_code == status_code, "%s instad of %s" % (actual_code, status_code)


    def assertRedirects(self, response, url=None):
        """
        reimplement this in case it's a WebOp response
        and it seems to be screwing up in a few places too
        thus the localhost exception
        """
        self.assertStatusCode(response, (301, 302))
        location = None
        if hasattr(response, 'location'):
            location = response.location
        else:
            location = response['location']
        if url is not None:
            assert url in location, location
        #return super(django_webtest.WebTest, self).assertRedirects(response, url)
        #assert url in response.location, "redirected to %s instead of %s" % (response.location, url)


    def assertContains(self, response, text):
        self.assertStatusCode(response, 200)

        if hasattr(response, "testbody"):
            t = response.testbody
        elif hasattr(response, "body"):
            t = response.body
        else:
            t = response.content

        if isinstance(text, bytes):
            text = text.decode()
        if isinstance(t, bytes):
            t = t.decode()
        assert text in t, "missing text %s" % text


##
## overall operation of the system
##

class ElectionBlackboxTests(WebTest):
    fixtures = ['users.json', 'election.json']
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

    def setup_login(self, from_scratch=False, **kwargs):
        if from_scratch:
            # a bogus call to set up the session
            self.client.get("/")
        # set up the session
        session = self.client.session
        if kwargs:
            user = auth_models.User.objects.get(**kwargs)
        else:
            user = self.user
        session['user'] = {'type': user.user_type, 'user_id': user.user_id}
        session.save()

        # set up the app, too
        # this does not appear to work, boohoo
        #session = self.app.session
        #session['user'] = {'type': self.user.user_type, 'user_id': self.user.user_id}

    def clear_login(self):
        session = self.client.session
        del session['user']
        session.save()        

    def test_election_params(self):
        response = self.client.get("/helios/elections/params")
        self.assertEqual(response.content, views.ELGAMAL_PARAMS_LD_OBJECT.serialize().encode('utf-8'))

    def test_election_404(self):
        response = self.client.get("/helios/elections/foobar")
        self.assertStatusCode(response, 404)

    def test_election_bad_trustee(self):
        response = self.client.get("/helios/t/%s/foobar@bar.com/badsecret" % self.election.short_name)
        self.assertStatusCode(response, 404)

    def test_get_election_shortcut(self):
        response = self.client.get("/helios/e/%s" % self.election.short_name, follow=True)
        self.assertContains(response, self.election.description_bleached)
        
    def test_get_election_raw(self):
        response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
        self.assertEqual(response.content, self.election.toJSON().encode('utf-8'))
    
    def test_get_election(self):
        response = self.client.get("/helios/elections/%s/view" % self.election.uuid, follow=False)
        self.assertContains(response, self.election.description_bleached)

    def test_get_election_questions(self):
        response = self.client.get("/helios/elections/%s/questions" % self.election.uuid, follow=False)
        for q in self.election.questions:
            self.assertContains(response, q['question'])
    
    def test_get_election_trustees(self):
        response = self.client.get("/helios/elections/%s/trustees" % self.election.uuid, follow=False)
        for t in self.election.trustee_set.all():
            self.assertContains(response, t.name)

    def test_get_election_voters(self):
        response = self.client.get("/helios/elections/%s/voters/list" % self.election.uuid, follow=False)
        # check total count of voters
        if self.election.num_voters == 0:
            self.assertContains(response, "no voters")
        else:
            self.assertContains(response, "(of %s)" % self.election.num_voters)

    def test_get_election_voters_raw(self):
        response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
        self.assertEqual(len(response.json()), self.election.num_voters)
        
    def test_election_creation_not_logged_in(self):
        response = self.client.post("/helios/elections/new", {
                "short_name" : "test-complete",
                "name" : "Test Complete",
                "description" : "A complete election test",
                "election_type" : "referendum",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p" : "False"})

        self.assertRedirects(response, "/auth/?return_url=/helios/elections/new")
    
    def test_election_edit(self):
        self.setup_login(from_scratch=True)
        response = self.client.get("/helios/elections/%s/edit" % self.election.uuid)
        response = self.client.post("/helios/elections/%s/edit" % self.election.uuid, {
                "short_name" : self.election.short_name + "-2",
                "name" : self.election.name,
                "description" : self.election.description,
                "election_type" : self.election.election_type,
                "use_voter_aliases": self.election.use_voter_aliases,
                'csrf_token': self.client.session['csrf_token']
                })

        self.assertRedirects(response, "/helios/elections/%s/view" % self.election.uuid)

        new_election = models.Election.objects.get(uuid = self.election.uuid)
        self.assertEqual(new_election.short_name, self.election.short_name + "-2")

    def test_get_election_stats(self):
        self.setup_login(from_scratch=True, user_id='mccio@github.com', user_type='google')
        response = self.client.get("/helios/stats/", follow=False)
        self.assertStatusCode(response, 200)
        response = self.client.get("/helios/stats/force-queue", follow=False)
        self.assertRedirects(response, "/helios/stats/")
        response = self.client.get("/helios/stats/elections", follow=False)
        self.assertStatusCode(response, 200)
        response = self.client.get("/helios/stats/problem-elections", follow=False)
        self.assertStatusCode(response, 200)
        response = self.client.get("/helios/stats/recent-votes", follow=False)
        self.assertStatusCode(response, 200)
        self.clear_login()
        response = self.client.get("/helios/stats/", follow=False)
        self.assertStatusCode(response, 403)
        self.setup_login()
        response = self.client.get("/helios/stats/", follow=False)
        self.assertStatusCode(response, 403)
        self.clear_login()

    def _setup_complete_election(self, election_params=None):
        "do the setup part of a whole election"

        # REPLACE with params?
        self.setup_login(from_scratch=True)

        # create the election
        full_election_params = {
            "short_name" : "test-complete",
            "name" : "Test Complete",
            "description" : "A complete election test",
            "election_type" : "referendum",
            "use_voter_aliases": "0",
            "use_advanced_audit_features": "1",
            "private_p" : "False",
            'csrf_token': self.client.session['csrf_token']
        }

        # override with the given
        full_election_params.update(election_params or {})

        response = self.client.post("/helios/elections/new", full_election_params)
        self.assertRedirects(response)

        # we are redirected to the election, let's extract the ID out of the URL
        election_id = re.search('/elections/([^/]+)/', str(response['location']))
        self.assertIsNotNone(election_id, "Election id not found in redirect: %s" % str(response['location']))
        election_id = election_id.group(1)

        # helios is automatically added as a trustee

        # check that helios is indeed a trustee
        response = self.client.get("/helios/elections/%s/trustees/view" % election_id)
        self.assertContains(response, "Trustee #1")

        # add a few voters with an improperly placed email address
        FILE = "helios/fixtures/voter-badfile.csv"
        voters_file = open(FILE)
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'voters_file': voters_file})
        voters_file.close()
        self.assertContains(response, "HOLD ON")

        # add a few voters, via file upload
        # this file now includes a UTF-8 encoded unicode character
        # yes I know that's not how you spell Ernesto.
        # I just needed some unicode quickly.
        FILE = "helios/fixtures/voter-file.csv"
        voters_file = open(FILE)
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'voters_file': voters_file})
        voters_file.close()
        self.assertContains(response, "first few rows of this file")

        # now we confirm the upload
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'confirm_p': "1"})
        self.assertRedirects(response, "/helios/elections/%s/voters/list" % election_id)

        # Try a latin-1 encoded file
        FILE = "helios/fixtures/voter-file-latin1.csv"
        voters_file = open(FILE, mode='rb')
        response = self.client.post("/helios/elections/%s/voters/upload" % election_id, {'voters_file': voters_file})
        voters_file.close()
        self.assertContains(response, "first few rows of this file")
        
        # and we want to check that there are now voters
        response = self.client.get("/helios/elections/%s/voters/" % election_id)
        NUM_VOTERS = 4
        self.assertEqual(len(response.json()), NUM_VOTERS)

        # let's get a single voter
        single_voter = models.Election.objects.get(uuid = election_id).voter_set.all()[0]
        response = self.client.get("/helios/elections/%s/voters/%s" % (election_id, single_voter.uuid))
        self.assertContains(response, '"uuid": "%s"' % single_voter.uuid)

        response = self.client.get("/helios/elections/%s/voters/foobar" % election_id)
        self.assertStatusCode(response, 404)
        
        # add questions
        response = self.client.post("/helios/elections/%s/save_questions" % election_id, {
                'questions_json': utils.to_json([{"answer_urls": ["http://example.com",None], "answers": ["Alice", "Bob"], "choice_type": "approval", "max": 1, "min": 0, "question": "Who should be president?", "result_type": "absolute", "short_name": "Who should be president?", "tally_type": "homomorphic"}]),
                'csrf_token': self.client.session['csrf_token']})

        self.assertContains(response, "SUCCESS")

        # freeze election
        response = self.client.post("/helios/elections/%s/freeze" % election_id, {
                "csrf_token" : self.client.session['csrf_token']})
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        # email the voters
        num_messages_before = len(mail.outbox)
        response = self.client.post("/helios/elections/%s/voters/email" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                "subject" : "your password",
                "body" : "time to vote",
                "suppress_election_links" : "0",
                "send_to" : "all"
                })
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)
        num_messages_after = len(mail.outbox)
        self.assertEqual(num_messages_after - num_messages_before, NUM_VOTERS)

        email_message = mail.outbox[num_messages_before]
        assert "your password" in email_message.subject, "bad subject in email"

        # get the username and password
        username = re.search('voter ID: (.*)', email_message.body).group(1)
        password = re.search('password: (.*)', email_message.body).group(1)

        # now log out as administrator
        self.clear_login()
        self.assertEqual('user' in self.client.session, False)

        # return the voter username and password to vote
        return election_id, username, password

    def _cast_ballot(self, election_id, username, password, need_login=True, check_user_logged_in=False):
        """
        check_user_logged_in looks for the "you're already logged" message
        """
        # vote by preparing a ballot via the server-side encryption
        response = self.app.post("/helios/elections/%s/encrypt-ballot" % election_id,
                   params={'answers_json': utils.to_json([[1]])})
        self.assertContains(response, "answers")

        # parse it as an encrypted vote with randomness, and make sure randomness is there
        the_ballot = utils.from_json(response.testbody)
        assert 'randomness' in the_ballot['answers'][0], "no randomness"
        assert len(the_ballot['answers'][0]['randomness']) == 2, "not enough randomness"
        
        # parse it as an encrypted vote, and re-serialize it
        ballot = datatypes.LDObject.fromDict(the_ballot, type_hint='legacy/EncryptedVote')
        encrypted_vote = ballot.serialize()
        
        # cast the ballot
        response = self.app.post("/helios/elections/%s/cast" % election_id,
                   params={'encrypted_vote': encrypted_vote})
        self.assertRedirects(response, "%s/helios/elections/%s/cast_confirm" % (settings.SECURE_URL_HOST, election_id))

        cast_confirm_page = response.follow()
        
        if need_login:
            if check_user_logged_in:
                self.assertContains(cast_confirm_page, "You are logged in as")
                self.assertContains(cast_confirm_page, "requires election-specific credentials")

            # set the form
            login_form = cast_confirm_page.form
            login_form['voter_id'] = username
            login_form['password'] = password

            response = login_form.submit()
        else:
            # here we should be at the cast-confirm page and logged in
            self.assertContains(cast_confirm_page, "CAST this ballot")

            # confirm the vote, now with the actual form
            cast_form = cast_confirm_page.form
        
            if 'status_update' in list(cast_form.fields.keys()):
                cast_form['status_update'] = False
            response = cast_form.submit()

        self.assertRedirects(response, "%s/helios/elections/%s/cast_done" % (settings.URL_HOST, election_id))

        # at this point an email should have gone out to the user
        # at position num_messages after, since that was the len() before we cast this ballot
        email_message = mail.outbox[len(mail.outbox) - 1]
        url = re.search('https?://[^/]+(/[^ \n]*)', email_message.body).group(1)

        # check that we can get at that URL
        if not need_login:
            # confusing piece: if need_login is True, that means it was a public election
            # that required login before casting a ballot.
            # so if need_login is False, it was a private election, and we do need to re-login here
            # we need to re-login if it's a private election, because all data, including ballots
            # is otherwise private
            login_page = self.app.get("/helios/elections/%s/password_voter_login" % election_id)

            # if we redirected, that's because we can see the page, I think
            if login_page.status_int != 302:
                login_form = login_page.form
                
                # try with extra spaces
                login_form['voter_id'] = '  ' + username + '   '
                login_form['password'] = '  ' + password + '      '
                login_form.submit()
            
        response = self.app.get(url, auto_follow=True)
        self.assertContains(response, ballot.hash)
        self.assertContains(response, html_escape(encrypted_vote))

        # if we request the redirect to cast_done, the voter should be logged out, but not the user
        response = self.app.get("/helios/elections/%s/cast_done" % election_id)

        # FIXME: how to check this? We can't do it by checking session that we're doign webtes
        # assert not self.client.session.has_key('CURRENT_VOTER')

    def _do_tally(self, election_id):
        # log back in as administrator
        self.setup_login()

        # encrypted tally
        response = self.client.post("/helios/elections/%s/compute_tally" % election_id, {
                "csrf_token" : self.client.session['csrf_token']                
                })
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        # should trigger helios decryption automatically
        self.assertNotEqual(models.Election.objects.get(uuid=election_id).get_helios_trustee().decryption_proofs, None)

        # combine decryptions
        response = self.client.post("/helios/elections/%s/combine_decryptions" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                })

        # after tallying, we now go back to election_view
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        # check that we can't get the tally yet
        response = self.client.get("/helios/elections/%s/result" % election_id)
        self.assertStatusCode(response, 403)

        # release
        response = self.client.post("/helios/elections/%s/release_result" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                })

        # check that tally matches
        response = self.client.get("/helios/elections/%s/result" % election_id)
        self.assertEqual(response.json(), [[0,1]])
        
    def test_do_complete_election(self):
        election_id, username, password = self._setup_complete_election()
        
        # cast a ballot while not logged in
        self._cast_ballot(election_id, username, password, check_user_logged_in=False)

        # cast a ballot while logged in as a user (not a voter)
        self.setup_login()

        ## for now the above does not work, it's a testing problem
        ## where the cookie isn't properly set. We'll have to figure this out.
        ## FIXME FIXME FIXME 
        #self._cast_ballot(election_id, username, password, check_user_logged_in=True)
        self._cast_ballot(election_id, username, password, check_user_logged_in=False)
        self.clear_login()

        self._do_tally(election_id)

    def test_do_complete_election_private(self):
        # private election
        election_id, username, password = self._setup_complete_election({'private_p' : "True"})

        # get the password_voter_login_form via the front page
        # (which will test that redirects are doing the right thing)
        response = self.app.get("/helios/elections/%s/view" % election_id)

        # ensure it redirects
        self.assertRedirects(response, "/helios/elections/%s/password_voter_login?%s" % (election_id, urlencode({"return_url": "/helios/elections/%s/view" % election_id})))

        login_form = response.follow().form

        login_form['voter_id'] = username
        login_form['password'] = password

        response = login_form.submit()
        self.assertRedirects(response, "/helios/elections/%s/view" % election_id)

        self._cast_ballot(election_id, username, password, need_login = False)
        self._do_tally(election_id)

    def test_election_voters_eligibility(self):
        # create the election
        self.setup_login(from_scratch=True)
        response = self.client.post("/helios/elections/new", {
                "short_name" : "test-eligibility",
                "name" : "Test Eligibility",
                "description" : "An election test for voter eligibility",
                "election_type" : "election",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p" : "False",
                'csrf_token': self.client.session['csrf_token']})

        election_id = re.match("(.*)/elections/(.*)/view", str(response['Location']))
        self.assertIsNotNone(election_id, "Election id not found in redirect: %s" % str(response['Location']))
        election_id = election_id.group(2)

        # update eligiblity
        response = self.client.post("/helios/elections/%s/voters/eligibility" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                "eligibility": "openreg"})

        self.clear_login()
        response = self.client.get("/helios/elections/%s/voters/list" % election_id)
        self.assertContains(response, "Anyone can vote")

        self.setup_login()
        response = self.client.post("/helios/elections/%s/voters/eligibility" % election_id, {
                "csrf_token" : self.client.session['csrf_token'],
                "eligibility": "closedreg"})

        self.clear_login()
        response = self.client.get("/helios/elections/%s/voters/list" % election_id)
        self.assertContains(response, "Only the voters listed here")

    def test_do_complete_election_with_trustees(self):
        """
        FIXME: do the this test
        """
        pass


class EmailOptOutTests(TestCase):
    fixtures = ['users.json']
    allow_database_queries = True

    def setUp(self):
        self.user = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')

    def test_email_hashing(self):
        """Test email hashing utility function"""
        email = "test@example.com"
        hash1 = utils.hash_email(email)
        hash2 = utils.hash_email(email.upper())  # Should be same after normalization
        hash3 = utils.hash_email("  " + email + "  ")  # Should be same after strip
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)  # SHA-256 hex length

    def test_hmac_generation_and_verification(self):
        """Test HMAC confirmation code generation and verification"""
        email = "test@example.com"
        action = "optout"
        
        code = utils.generate_email_confirmation_code(email, action)
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 64)  # SHA-256 hex length
        
        # Valid verification
        self.assertTrue(utils.verify_email_confirmation_code(email, action, code))
        
        # Invalid verifications
        self.assertFalse(utils.verify_email_confirmation_code(email, "optin", code))  # Wrong action
        self.assertFalse(utils.verify_email_confirmation_code("other@example.com", action, code))  # Wrong email
        self.assertFalse(utils.verify_email_confirmation_code(email, action, "invalidcode"))  # Wrong code

    def test_email_opt_out_model(self):
        """Test EmailOptOut model functionality"""
        email = "test@example.com"
        
        # Initially not opted out
        self.assertFalse(models.EmailOptOut.is_opted_out(email))
        
        # Add opt-out
        opt_out = models.EmailOptOut.add_opt_out(email, "test-agent", "127.0.0.1")
        self.assertIsNotNone(opt_out)
        
        # Now should be opted out
        self.assertTrue(models.EmailOptOut.is_opted_out(email))
        
        # Adding again should return existing record
        opt_out2 = models.EmailOptOut.add_opt_out(email)
        self.assertEqual(opt_out.id, opt_out2.id)
        
        # Remove opt-out
        removed = models.EmailOptOut.remove_opt_out(email)
        self.assertTrue(removed)
        
        # Should no longer be opted out
        self.assertFalse(models.EmailOptOut.is_opted_out(email))
        
        # Removing again should return False
        removed2 = models.EmailOptOut.remove_opt_out(email)
        self.assertFalse(removed2)

    def test_voter_registration_with_opted_out_email(self):
        """Test that voter registration fails for opted-out emails"""
        email = "opted-out@example.com"
        
        # Opt out the email
        models.EmailOptOut.add_opt_out(email)
        
        # Create a user with opted-out email
        user = auth_models.User.objects.create(
            user_type='password',
            user_id=email,
            name='Test User'
        )
        
        # Create an election
        election, _ = models.Election.get_or_create(
            short_name='test-optout',
            name='Test Opt-Out Election',
            description='Test Election for Opt-Out',
            admin=self.user
        )
        
        # Trying to register should raise ValueError
        with self.assertRaises(ValueError):
            models.Voter.register_user_in_election(user, election)

    def test_opted_out_check_in_tasks(self):
        """Test that tasks check for opted-out status correctly"""
        email = "voter@example.com"
        
        # Create an election and voter  
        election, _ = models.Election.get_or_create(
            short_name='test-email',
            name='Test Email Election', 
            description='Test Election for Email',
            admin=self.user
        )
        
        voter = models.Voter.objects.create(
            uuid=str(uuid.uuid4()),
            election=election,
            voter_email=email,
            voter_name="Test Voter"
        )
        
        # Test the opt-out checking logic directly
        # Before opt-out, voter should not be skipped
        self.assertFalse(models.EmailOptOut.is_opted_out(email))
        
        from unittest.mock import patch
        
        # Test that single_voter_email DOES send emails before opt-out
        with patch.object(models.Voter, 'send_message') as mock_send_message:
            
            # Verify voter setup
            self.assertEqual(voter.voter_email, email)
            self.assertFalse(models.EmailOptOut.is_opted_out(email))
            
            # Call single_voter_email before opt-out is applied
            result = tasks.single_voter_email.apply(args=[voter.uuid, "email/simple_subject.txt", "email/simple_body.txt", {}])
            
            # Debug: check if task completed successfully
            self.assertTrue(result.successful())
            
            # The send_message method should have been called because voter is not opted out
            mock_send_message.assert_called_once()
        
        # Now opt out the email
        models.EmailOptOut.add_opt_out(email)
        
        # After opt-out, voter should be skipped
        self.assertTrue(models.EmailOptOut.is_opted_out(email))
        
        # Test that single_voter_email does NOT send emails after opt-out
        with patch.object(models.Voter, 'send_message') as mock_send_message:
            
            # Call single_voter_email after opt-out is applied
            tasks.single_voter_email.apply(args=[voter.uuid, "email/simple_subject.txt", "email/simple_body.txt", {}])
            
            # The send_message method should not have been called because voter is opted out
            mock_send_message.assert_not_called()

    def test_email_contains_unsubscribe_link(self):
        """Test that emails sent to voters contain unsubscribe links"""
        from helios.view_utils import render_template_raw
        
        email = "voter@example.com"
        
        # Create an election and voter
        election, _ = models.Election.get_or_create(
            short_name='test-unsubscribe',
            name='Test Unsubscribe Election',
            description='Test Election for Unsubscribe Links',
            admin=self.user
        )
        
        voter = models.Voter.objects.create(
            uuid=str(uuid.uuid4()),
            election=election,
            voter_email=email,
            voter_name="Test Voter"
        )
        
        # Generate the unsubscribe URL as the task would
        unsubscribe_code = utils.generate_email_confirmation_code(email, 'optout')
        
        # Prepare template context similar to what single_voter_email does
        template_vars = {
            'election': election,
            'voter': voter,
            'election_url': 'http://example.com/election/123',
            'election_vote_url': 'http://example.com/election/123/vote',
            'custom_message': 'Please vote!',
            'unsubscribe_url': f'http://example.com/optout/confirm/{email}/{unsubscribe_code}/',
            'unsubscribe_code': unsubscribe_code
        }
        
        # Render the email body template
        body = render_template_raw(None, 'email/vote_body.txt', template_vars)
        
        # Verify the unsubscribe link is in the body
        self.assertIn('To stop receiving all emails from Helios', body)
        self.assertIn('/optout/confirm/', body)
        self.assertIn(email, body)
        self.assertIn(unsubscribe_code, body)


class EmailOptOutViewTests(WebTest):
    """Test the opt-out/opt-in web views and templates"""
    allow_database_queries = True

    def test_optout_form_renders(self):
        """Test that opt-out form page renders correctly"""
        response = self.client.get('/optout/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Opt Out of Helios Emails')
        self.assertContains(response, 'Enter your email address to stop receiving all emails')
        self.assertContains(response, '<form class="prettyform" method="POST" action="">')
        self.assertContains(response, 'name="email"')

    def test_optin_form_renders(self):
        """Test that opt-in form page renders correctly"""
        response = self.client.get('/optin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Opt Back Into Helios Emails')
        self.assertContains(response, 'Enter your email address to resume receiving emails')
        self.assertContains(response, '<form class="prettyform" method="POST" action="">')
        self.assertContains(response, 'name="email"')

    def test_optout_request_sends_email(self):
        """Test that opt-out request sends confirmation email"""
        with self.settings(DEFAULT_FROM_EMAIL='test@helios.org'):
            response = self.client.post('/optout/', {'email': 'test@example.com'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/optout/success/')
            
            # Check that email was sent
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].subject, 'Confirm your opt-out from Helios emails')
            self.assertIn('test@example.com', mail.outbox[0].to)
            self.assertIn('/optout/confirm/test@example.com/', mail.outbox[0].body)

    def test_optout_success_page_renders(self):
        """Test that opt-out success page renders correctly"""
        response = self.client.get('/optout/success/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Opt-Out Confirmation Sent')
        self.assertContains(response, 'We have sent you a confirmation email')

    def test_optout_confirm_with_valid_code(self):
        """Test opt-out confirmation with valid HMAC code"""
        email = 'test@example.com'
        code = utils.generate_email_confirmation_code(email, 'optout')
        
        response = self.client.get(f'/optout/confirm/{email}/{code}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully Opted Out')
        self.assertContains(response, email)
        
        # Verify email is now opted out
        self.assertTrue(models.EmailOptOut.is_opted_out(email))

    def test_optout_confirm_with_invalid_code(self):
        """Test opt-out confirmation with invalid HMAC code"""
        email = 'test@example.com'
        
        response = self.client.get(f'/optout/confirm/{email}/invalidcode/')
        self.assertEqual(response.status_code, 404)

    def test_optin_request_for_opted_out_email(self):
        """Test that opt-in request sends confirmation email for opted-out address"""
        email = 'test@example.com'
        models.EmailOptOut.add_opt_out(email)
        
        with self.settings(DEFAULT_FROM_EMAIL='test@helios.org'):
            response = self.client.post('/optin/', {'email': email})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/optin/success/')
            
            # Check that email was sent
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].subject, 'Confirm your opt-in to Helios emails')
            self.assertIn(email, mail.outbox[0].to)
            self.assertIn(f'/optin/confirm/{email}/', mail.outbox[0].body)

    def test_optin_request_for_non_opted_out_email(self):
        """Test that opt-in request shows message for non-opted-out address"""
        email = 'test@example.com'
        
        response = self.client.post('/optin/', {'email': email})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email Not Found')
        self.assertContains(response, f'The email address <strong>{email}</strong> is not currently opted out')

    def test_optin_confirm_with_valid_code(self):
        """Test opt-in confirmation with valid HMAC code"""
        email = 'test@example.com'
        models.EmailOptOut.add_opt_out(email)
        code = utils.generate_email_confirmation_code(email, 'optin')
        
        response = self.client.get(f'/optin/confirm/{email}/{code}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully Opted Back In')
        self.assertContains(response, email)
        
        # Verify email is no longer opted out
        self.assertFalse(models.EmailOptOut.is_opted_out(email))


class VotersCSVDownloadTests(TestCase):
    """Test voter CSV download functionality"""
    fixtures = ['users.json']
    
    def setUp(self):
        self.admin = auth_models.User.objects.get(user_id='ben@adida.net', user_type='google')
        self.election, _ = models.Election.get_or_create(
            short_name='test-csv',
            name='Test CSV Election',
            description='Test Election for CSV Download',
            admin=self.admin)
        
        # Ensure the election has a UUID
        if not self.election.uuid:
            self.election.uuid = str(uuid.uuid4())
            self.election.save()
        
        # Add some voters
        self.voter1 = models.Voter(
            uuid=str(uuid.uuid4()),
            election=self.election,
            voter_email='voter1@example.com',
            voter_name='Voter One',
            voter_login_id='voter1'
        )
        self.voter1.save()
        
        self.voter2 = models.Voter(
            uuid=str(uuid.uuid4()),
            election=self.election,
            voter_email='voter2@example.com',
            voter_name='Voter Two',
            voter_login_id='voter2',
            vote_hash='test-hash-123',
            cast_at=datetime.datetime.now()
        )
        self.voter2.user = auth_models.User.objects.filter(user_type='google')[0]
        self.voter2.save()
        
    def test_csv_download_as_admin(self):
        """Test CSV download as admin shows all fields"""
        # Set session to simulate admin login - check that admin matches election admin
        self.assertEqual(self.election.admin, self.admin)
        
        # Set up the session properly
        session = self.client.session
        session['user'] = {
            'type': self.admin.user_type,
            'user_id': self.admin.user_id
        }
        session.save()
        
        response = self.client.get(f'/helios/elections/{self.election.uuid}/voters/download-csv')
        
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="voters_test-csv_', response['Content-Disposition'])
        
        # Check CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().splitlines()
        headers = lines[0].split(',')
        
        # Admin should see all fields
        self.assertEqual(headers, ['Login', 'Email Address', 'Name', 'Voter Type', 'Smart Ballot Tracker', 'Vote Cast At'])
        
        # Check we have the right number of voters
        self.assertEqual(len(lines), 3)  # Header + 2 voters
    
    def test_csv_download_as_non_admin(self):
        """Test CSV download as non-admin shows limited fields"""
        response = self.client.get(f'/helios/elections/{self.election.uuid}/voters/download-csv')
        
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Check CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().splitlines()
        headers = lines[0].split(',')
        
        # Non-admin should see limited fields
        self.assertEqual(headers, ['Name', 'Voter Type', 'Smart Ballot Tracker', 'Vote Cast At'])
        
    def test_csv_download_with_aliases(self):
        """Test CSV download with voter aliases enabled"""
        self.election.use_voter_aliases = True
        self.election.save()
        
        # Set aliases
        self.voter1.alias = 'Alias One'
        self.voter1.save()
        self.voter2.alias = 'Alias Two'
        self.voter2.save()
        
        response = self.client.get(f'/helios/elections/{self.election.uuid}/voters/download-csv')
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        headers = [h.strip() for h in lines[0].split(',')]
        
        # With aliases, should show alias instead of name
        self.assertEqual(headers, ['Alias', 'Smart Ballot Tracker', 'Vote Cast At'])
        
    def test_csv_download_with_search(self):
        """Test CSV download with search filter"""
        # Set session to simulate admin login
        session = self.client.session
        session['user'] = {
            'type': self.admin.user_type,
            'user_id': self.admin.user_id
        }
        session.save()
        
        response = self.client.get(f'/helios/elections/{self.election.uuid}/voters/download-csv?q=One')
        
        content = response.content.decode('utf-8')
        lines = content.strip().splitlines()
        # Should only have header + 1 voter
        self.assertEqual(len(lines), 2)
