import flask
import sqlalchemy
import psycopg2
import flask.ext.sqlalchemy
import xlrd
import re 
import datetime
from xldate import xldate_as_tuple

# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:qcsales@localhost/mydatabase'
db = flask.ext.sqlalchemy.SQLAlchemy(app)
db.create_all()

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product = db.Column(db.Unicode, unique=True)
   
class Rep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repID = db.Column(db.Unicode, unique=True)
    last_name = db.Column(db.Unicode)
    first_name = db.Column(db.Unicode)
    employeeID = db.Column(db.Unicode)
    date_of_hire = db.Column(db.Date)
    department = db.Column(db.Unicode)
    channel = db.Column(db.Unicode)
    manager_id = db.Column(db.Integer, db.ForeignKey('rep.id'))
    manager = db.relationship('Rep', remote_side=[id])
    def name(self):
        return u"%s, %s" % (self.last_name, self.first_name)

class Industry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sic = db.Column(db.Integer)
    naics = db.Column(db.Integer)
    industry_name = db.Column(db.Unicode)
    def __init__(self, sic=None, naics=None, industry_name=None):
        self.sic = sic
        self.naics = naics
        self.industry_name = industry_name
   
class ParentAgency(db.Model):
    id = db.Column(db.Integer, primary_key=True)   
    parent = db.Column(db.Unicode)
    
class Advertiser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advertiser = db.Column(db.Unicode)
    parent_agency_id = db.Column(db.Integer, db.ForeignKey('parent_agency.id'))
    parent_agency = db.relationship('ParentAgency')
    industry_id = db.Column(db.Integer, db.ForeignKey('industry.id'))
    industry = db.relationship('Industry')

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign = db.Column(db.Unicode)
    type = db.Column(db.Unicode)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', lazy='joined')
    channel = db.Column(db.Unicode)    
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertiser.id'))
    advertiser = db.relationship('Advertiser')    
    rep_id = db.Column(db.Integer, db.ForeignKey('rep.id'))
    rep = db.relationship('Rep')
    cp = db.Column(db.Unicode)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    cpm_price = db.Column(db.Float)
    contracted_impr = db.Column(db.Integer)
    contracted_deal = db.Column(db.Float)
    revised_deal = db.Column(db.Float)
    def get_absolute_url(self):
        return u"/note/%s/" % self.campaign
    def getBookedRev(self, myDate):
        a = self.booked_set.filter(date = myDate)
        if a:
            return a[0].bookedRev
        else:  
            return 0
    def getActualRev(self, myDate):
        a = self.actual_set.filter(date = myDate)
        if a:
            return a[0].actualRev
        else:  
            return 0

class Booked(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'))
    campaign = db.relationship('Campaign')
    date = db.Column(db.Date)
    bookedRev = db.Column(db.Float)
    
class Actual(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'))
    campaign = db.relationship('Campaign')    
    date = db.Column(db.Date)    
    actualRev = db.Column(db.Float)    

# Create the database tables.

def populateDB():    
    # Create and fill Tables        
    wb = xlrd.open_workbook('C:/Users/rthomas/Desktop/DatabaseProject/SalesMetricData.xls')
    wb.sheet_names()
    sh = wb.sheet_by_name('Industry')     
    for rownum in range(1,538): #sh.nrows):
        sic = sh.cell(rownum,0).value
        naics = sh.cell(rownum,1).value
        industry = sh.cell(rownum,2).value            
        if isinstance(sic,float):
            sic = int(sic)
        else:
            sic = None 
        if isinstance(naics,float):
            naics = int(naics)
        else:
            naics = None    
        a = Industry(sic, naics, industry)
        db.session.add(a)
    db.session.commit()
#        print("sic: " + str(sic) + "   naics: " + str(naics) + "  industry:" + industry)        
    
    sh = wb.sheet_by_name('AdvertiserParent')     
    for rownum in range(0, 1074): #sh.nrows):
        parent = sh.cell(rownum,0).value
        a = ParentAgency(parent = parent)
        db.session.add(a)
    
    db.session.commit()
    
    sh = wb.sheet_by_name('Advertiser')
     
    for rownum in range(1, sh.nrows):
        advertiser = sh.cell(rownum,0).value
        parent_name = sh.cell(rownum,1).value
        sic = sh.cell(rownum,2).value
        naics = sh.cell(rownum,3).value
        industry_name = sh.cell(rownum,4).value
        if re.match('[(#]', industry_name):
            industry = None
        else:
            if isinstance(sic,float):
                sic = int(sic)
            else:
                sic = None
            if isinstance(naics,float):
                naics = int(naics)
            else:
                naics = None
            industry =  get_or_create(db.session, Industry, sic = sic, naics = naics, industry_name = industry_name)  
        parent = get_or_create(db.session, ParentAgency, parent = parent_name)
        adv = get_or_create(db.session, Advertiser, advertiser = advertiser)
        adv.parent_agency = parent
        adv.industry = industry
        db.session.commit()
    
    ###   Rep table    
       
    sh = wb.sheet_by_name('RepID')
     
    for rownum in range(1, 84):
        repID = sh.cell(rownum,0).value
        last_name = sh.cell(rownum,1).value
        first_name = sh.cell(rownum,2).value
        employeeID = sh.cell(rownum,3).value    
        department = sh.cell(rownum,8).value  
        channel = sh.cell(rownum,9).value    
        if isinstance(employeeID, float):
            employeeID = str(int(employeeID))
        if isinstance(sh.cell(rownum,4).value, float):
            try:
                date_of_hire = datetime.date(int(sh.cell(rownum,5).value), int(sh.cell(rownum,6).value), int(sh.cell(rownum,7).value))
            except:
                date_of_hire = None
        else:
            date_of_hire = None    
        try:
            mgr = db.session.query(Rep).filter_by(repID = sh.cell(rownum,10).value).first()
        except:
            mgr = None                      
        a = Rep(repID = repID, last_name = last_name, first_name = first_name, employeeID = employeeID, date_of_hire = date_of_hire, department = department, channel = channel, manager = mgr)
        db.session.add(a)
        db.session.commit()
    
###  Campaign Table

    sh = wb.sheet_by_name('Campaign')
     
    for rownum in range(1,sh.nrows):
        campaign = sh.cell(rownum,0).value
        t = sh.cell(rownum,1).value
        product = get_or_create(db.session, Product, product = sh.cell(rownum,2).value)
        channel = sh.cell(rownum,3).value
        advertiser = get_or_create(db.session, Advertiser, advertiser = sh.cell(rownum,4).value)
        rep = get_or_create(db.session, Rep, repID = sh.cell(rownum,5).value)
        cp = sh.cell(rownum,6).value
        if isinstance(sh.cell(rownum,7).value, float):
            try:
                start_date = datetime.date(int(sh.cell(rownum,7).value), int(sh.cell(rownum,8).value), int(sh.cell(rownum,9).value))
            except:
                start_date = None
        else:
            start_date = None  
        if isinstance(sh.cell(rownum,10).value, float):
            try:
                end_date = datetime.date(int(sh.cell(rownum,10).value), int(sh.cell(rownum,11).value), int(sh.cell(rownum,12).value))
            except:
                end_date = None
        else:
            end_date = None    
        cpm_price = sh.cell(rownum,13).value
        if not isinstance(cpm_price, float):  
            cpm_price = None
        contracted_impr = sh.cell(rownum,14).value
        if isinstance(contracted_impr, float):
            contracted_impr = int(contracted_impr)
        else:
            contracted_impr = None
        contracted_deal = sh.cell(rownum,15).value
        if not isinstance(contracted_deal, float):  
            contracted_deal = None    
        revised_deal = sh.cell(rownum,16).value
        if not isinstance(revised_deal, float):  
            revised_deal = None            
        a = Campaign(campaign = campaign, type = t, product = product, channel = channel, advertiser = advertiser, 
                     rep = rep, cp = cp, start_date = start_date, end_date = end_date, cpm_price = cpm_price, 
                     contracted_impr = contracted_impr, contracted_deal = contracted_deal, revised_deal =revised_deal)    
        db.session.add(a)
        db.session.commit()
    
    # Fill revenue tables
    sh = wb.sheet_by_name('Actual')
    for rownum in range(1,sh.nrows):
        camp_str = sh.cell(rownum,0).value
        rep = db.session.query(Rep).filter_by(repID = sh.cell(rownum,1).value).first()
        product =  db.session.query(Product).filter_by(product = sh.cell(rownum,2).value).first()
        channel = sh.cell(rownum,3).value
        advertiser = db.session.query(Advertiser).filter_by(advertiser = sh.cell(rownum,4).value).first()
        start = xldate_as_tuple(sh.cell(rownum,5).value,0)[0:3]
        py_start = datetime.date(*start)
        end = xldate_as_tuple(sh.cell(rownum,6).value,0)[0:3]
        py_end = datetime.date(*end)              
        try:
            campaign = db.session.query(Campaign).filter_by(campaign = camp_str).first()
            for colnum in range(7,sh.ncols):
                rev = sh.cell(rownum,colnum).value
                if isinstance(rev,float) and rev != 0.0: 
                    mydate = xldate_as_tuple(sh.cell(0,colnum).value,0)[0:3]
                    pyDate = datetime.date(*mydate)
                    a = Actual(campaign=campaign, date=pyDate, actualRev=rev)
                    db.session.add(a)
        except:
            try:
                campaign = db.session.query(Campaign).filter_by(campaign = camp_str, repId = rep, channel=channel, product = product, advertiser = advertiser, start_date = py_start, end_date = py_end).first()
                for colnum in range(7,sh.ncols):                
                    rev = sh.cell(rownum,colnum).value
                    if isinstance(rev,float) and rev != 0.0:
                        mydate = xldate_as_tuple(sh.cell(0,colnum).value,0)[0:3]
                        pyDate = datetime.date(*mydate)
                        a = Actual(campaign=campaign, date=pyDate, actualRev=rev)
                        db.session.add(a)            
            except:
                pass
    db.session.commit()
    
    sh = wb.sheet_by_name('Booked')
    for rownum in range(1,sh.nrows):
        camp_str = sh.cell(rownum,0).value
        rep = db.session.query(Rep).filter_by(repID = sh.cell(rownum,1).value).first()
        product =  db.session.query(Product).filter_by(product = sh.cell(rownum,2).value).first()
        channel = sh.cell(rownum,3).value
        advertiser = db.session.query(Advertiser).filter_by(advertiser = sh.cell(rownum,4).value).first()
        start = xldate_as_tuple(sh.cell(rownum,5).value,0)[0:3]
        py_start = datetime.date(*start)
        end = xldate_as_tuple(sh.cell(rownum,6).value,0)[0:3]
        py_end = datetime.date(*end)              
        try:
            campaign = db.session.query(Campaign).filter_by(campaign = camp_str).first()
            for colnum in range(7,sh.ncols):
                rev = sh.cell(rownum,colnum).value
                if isinstance(rev,float) and rev != 0.0: 
                    mydate = xldate_as_tuple(sh.cell(0,colnum).value,0)[0:3]
                    pyDate = datetime.date(*mydate)
                    a = Booked(campaign=campaign, date=pyDate, bookedRev=rev)
                    db.session.add(a)
        except:
            try:
                campaign = db.session.query(Campaign).filter_by(campaign = camp_str, repId = rep, channel=channel, product = product, advertiser = advertiser, start_date = py_start, end_date = py_end).first()
                for colnum in range(7,sh.ncols):                
                    rev = sh.cell(rownum,colnum).value
                    if isinstance(rev,float) and rev != 0.0:
                        mydate = xldate_as_tuple(sh.cell(0,colnum).value,0)[0:3]
                        pyDate = datetime.date(*mydate)
                        a = Booked(campaign=campaign, date=pyDate, bookedRev=rev)
                        db.session.add(a)            
            except:
                pass
    db.session.commit()
    
    

def cleanDB():
    s = db.session
    s.query(Booked).delete()
    s.query(Actual).delete()
    s.query(Campaign).delete()    
    s.query(Advertiser).delete()
    s.query(Rep).delete()
    s.query(Product).delete()
    s.query(Industry).delete()
    s.query(ParentAgency).delete()
    s.commit()

#db.create_all()       
#cleanDB()
#populateDB()

query = db.session.query(Campaign)
#import pdb; pdb.set_trace()

#field = getattr(Campaign, "rep")
#field = getattr(field, "last_name")
#direction = getattr(field, "asc")
#query = query.order_by(direction())