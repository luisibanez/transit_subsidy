from django.utils.unittest.case import skipIf,skip
from datetime import datetime
from django.test import TestCase
from front.models import OfficeLocation
from django.contrib.auth.models import User
from transit_subsidy.models import TransitSubsidy,Mode,TransitSubsidyModes
import StringIO
import csv
from front.models import App,Person


class TransportationSubsidyViewTest(TestCase):
    fixtures = ['offices.json','transit_modes.json']

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def setUp(self):
        """
        Assumes valid user
        """
        self.user = User.objects.create_user('test_user','test_user@cfpb.gov','password')
        is_logged_in = self.client.login(username='test_user',password='password')
        #guard
        self.assertTrue(is_logged_in, 'Client not able to login?! Check fixture data or User creation method in setUp.')
              
        self.office = OfficeLocation.objects.order_by('city')[0]
        self.person = Person(user=self.user)
        self.person.first_name = 'Ted'
        self.person.last_name = 'Nugent'
        self.person.save()


    def tearDown(self):
        pass

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    def test_returning_users_should_see_submitted_data(self):
        self._set_transit_subsidy()
        response = self.client.get('/transit/')
        self.assertEquals(200,response.status_code)
        self.assertTrue( response.context['returning_user'], 'Hmmmm. Code thinks there is no returning user')
        self.assertEquals( {} , response.context['form'].errors)



    #Major work to be done with CSV
    @skip('Changing requirements. Lots to do after initial release')
    def test_csv_dump_should_work(self):
        self._set_transit_subsidy()
        response = self.client.get('/transit/csv')
        normalized = StringIO.StringIO(response.content)
        data = csv.DictReader(normalized)
        actual = None
        for item in data:
            actual = item  #too tired. end of day. should fix this
            # print item
        self.assertEquals( self.user.email, item['Email'] )
        self.assertEquals( 164,  int(item['Total Claim Amount']) )
       



    def test_that_successful_transit_request_redirects_to_thankyou(self):
       
        #The below was causing failure ONLY when executed in Jenkins:
        response = self.client.post('/transit/', self.get_good_post_data() )
        self.assertTemplateUsed(response,'transit_subsidy/thank_you.html')


    # Make sure any new required fields are added to self.get_good_post_data()
    def test_that_successful_transit_request_redirects_to_thankyou(self):
        #The below was causing failure ONLY when executed in Jenkins:
        response = self.client.post('/transit/', self.get_good_post_data() )
        self.assertTemplateUsed(response,'transit_subsidy/thank_you.html')


    def test_that_zipcode_error_is_present(self):
        bad_post_data = {'city':'LA','state':'CA','zip':''}
        response = self.client.post('/transit/', bad_post_data)
        print response.status_code
        self.assertFormError(response, 'form', 'origin_zip', u'This field is required.')

            
    def test_that_bad_form_data_redirects_back_to_form(self):
        bad_post_data = {}
        response = self.client.post('/transit/', bad_post_data)
#        print response.context
        self.assertTemplateUsed(response, 'transit_subsidy/index.html', 'Should be thankyou.html if OK.')
        
        
    def test_that_login_is_required(self):
        response = self.client.post('/account/login/?next=/transit/', {'username': 'test_user', 'password': 'password'})
        response = self.client.get('/transit/')
        self.assertEquals(200, response.status_code, "Should be a 200.")
        # self.assertTrue( self.client.login(username='test_user',password='password'), "Login failed for test_user." )
        
        
    def test_that_redirect_works_with_new_user(self):
        #make sure user is logged out!
        self.client.logout()
        response = self.client.get('/transit/')
        self.assertRedirects(response, '/login/?next=/transit/')


    def test_that_ts_template_is_fetched(self):
        response = self.client.get('/transit/')
        self.assertEqual(200, response.status_code, "Did't get to template assertion. Check login logic or db.")
        self.assertTemplateUsed(response,'transit_subsidy/index.html')

    def test_set_modes(self):
        self.set_modes()
        trans = TransitSubsidy.objects.all()[0]
        modes = TransitSubsidyModes.objects.filter(transit_subsidy=trans)
        self.assertEquals(50, modes[1].cost)

     
    def test_post_segment_data_should_be_OK(self):
        pd = self.get_good_post_data()
        pd.update( self.get_good_segment_data() )
        response = self.client.post('/transit/', pd)
        #print response
        self.assertTemplateUsed(response,'transit_subsidy/thank_you.html')
           


    #Util method
    def get_good_post_data(self):
        return {  'date_enrolled' : datetime.now(),
                  'timestamp' : datetime.now(),
                  'last_four_ssn': '1111',
                  'origin_street': '123 Main St.',
                  'origin_city':'Anytown',
                  'origin_state':'OO',
                  'origin_zip':'12345',
                  'destination': self.office.id,
                  'number_of_workdays': 20,
                  'daily_roundtrip_cost' : 8,
                  'daily_parking_cost': 4,
                  'amount': 16,
                  'total_commute_cost': 164,
                  'signature' : 'Ted Nugent'
                  }
    

    def get_good_segment_data(self):
        return {  #Metro
                  'segment-type_1' : '1',
                  'segment-amount_1' : '12',
                  'segment-other_1' : '',
                  #Dash
                  'segment-type_2' : '3',
                  'segment-amount_2' : '12',
                  'segment-other_2' : '',
                  #Other
                  'segment-type_3' : '9',
                  'segment-amount_3' : '5',
                  'segment-other_3' : 'The Bus',
                }

    def set_modes(self):
        #Metro
        self.modes = Mode.objects.all()
        trans = self._set_transit_subsidy()
        _modes = TransitSubsidyModes(transit_subsidy=trans, mode=self.modes[0], cost=100)
        _modes.save()
        
        #Dash
        _modes = TransitSubsidyModes(transit_subsidy=trans, mode=self.modes[1], cost=50)
        _modes.save()

        #Other
        _modes = TransitSubsidyModes(transit_subsidy=trans, mode=self.modes[4], cost=5, other_mode='ScooterBus')
        _modes.save()


    def _set_transit_subsidy(self):
        transit = TransitSubsidy()
        office = OfficeLocation.objects.order_by('city')[0]

        transit.user = self.user
        transit.last_four_ssn = 3333
        transit.destination = office
        transit.date_enrolled = '2011-06-23'

        transit.origin_street = '123 Main Street'
        transit.origin_city = 'Anytown'
        transit.origin_state = 'VA'
        transit.origin_zip = '22222'
       
        transit.number_of_workdays = 20
        transit.daily_roundtrip_cost = 8
        transit.daily_parking_cost = 4
        transit.amount = 120
        transit.total_commute_cost = 160
        transit.dc_wmta_smartrip_id = '123-123-123'
        transit.save()
        return transit

