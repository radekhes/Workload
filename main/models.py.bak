from main import db
import re
from sqlalchemy import Column, DateTime, Float, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.schema import FetchedValue
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.ext.declarative import declarative_base

#Base = declarative_base()
#metadata = Base.metadata
import datetime
#import datetime.datetime


class AdminTable(db.Model):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    encrypted_password = Column(String(255), nullable=False, server_default=FetchedValue())
    reset_password_token = Column(String(255), unique=True, server_default=FetchedValue())
    reset_password_sent_at = Column(DateTime, server_default=FetchedValue())
    remember_created_at = Column(DateTime, server_default=FetchedValue())
    sign_in_count = Column(Integer, nullable=False, server_default=FetchedValue())
    current_sign_in_at = Column(DateTime, server_default=FetchedValue())
    last_sign_in_at = Column(DateTime, server_default=FetchedValue())
    current_sign_in_ip = Column(String(255), server_default=FetchedValue())
    last_sign_in_ip = Column(String(255), server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    username = Column(String(255), unique=True, server_default=FetchedValue())


class Model(db.Model):
    __tablename__ = 'model'

    id = Column(Integer, primary_key=True)
    equation = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    year_id = Column(Integer, index=True, server_default=FetchedValue())
    modified_by= Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    name= Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
   
    def __init__(self, mod,year_id,n):
        self.equation = mod
        self.created_at = datetime.datetime.now()
        self.name=n
     #   self.updated_at = datetime.datetime.now()
        self.year_id = year_id

    def __repr__(self):
        return '%s' % self.id


class Model_Set_Entity(db.Model):
    __tablename__ = 'model_set_entity'

    id = Column(Integer, primary_key=True)
    specific_field = Column(Integer, server_default=FetchedValue())
    model_id=Column(Integer)
    low_thresh=Column(Integer)
    hi_thresh = Column(Integer)
    selection = Column(Integer)
    name=Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    modified_by= Column(String(255), nullable=False, unique=True, server_default=FetchedValue())

    def __init__(self, s_f, mod_id, sel,n, l_t, h_t):
        self.specific_field = s_f
        self.model_id = mod_id
        self.selection = sel
        self.name = n
        self.low_thresh=l_t
        self.hi_thresh=h_t
    
    def __repr__(self):
        return '%s' % self.id

class CourseStaff(db.Model):
    __tablename__ = 'course_staff'

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer,db.ForeignKey('courses.id'), index=True,  server_default=FetchedValue())
    staff_id = Column(Integer, db.ForeignKey('staff.id'), index=True, server_default=FetchedValue())
    workload = Column(Float, server_default=FetchedValue())
    is_coordinator = Column(Integer, server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    year_id = Column(Integer, index=True, server_default=FetchedValue())
    nt_hours = Column(Integer, index=True, server_default=FetchedValue())
    modified_by = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())

    def __init__(self,c_id,s_id,w,c,y_id,nt_h, mb='0'):
        self.course_id =c_id
        self.nt_hours=nt_h
        self.staff_id=s_id
        self.workload=w
        self.is_coordinator=c
        self.created_at=datetime.datetime.now()
        #self.updated_at = datetime.datetime.now()
        self.year_id = y_id
        self.modified_by=mb

    def __repr__(self):
        return '%s' % self.id


class Discipline(db.Model):
    __tablename__ = 'disciplines'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
   # year_id =Column(Integer, index=True, server_default=FetchedValue())



class Course(db.Model):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    code = Column(String(255), server_default=FetchedValue())
    title = Column(Text)
    trimester = Column(String(255), server_default=FetchedValue())
    expected_students = Column(Integer, server_default=FetchedValue())
    is_offered = Column(Integer, server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    status = Column(String(255), server_default=FetchedValue())
    student_factor = Column(Float, server_default=FetchedValue())
    course_discipline_id = Column(Integer, server_default=FetchedValue())
    year_id = Column(Integer, index=True, server_default=FetchedValue())
    num_lectures_week = Column(Integer, index=True, server_default=FetchedValue())
    lecture_duration  = Column(Integer, index=True, server_default=FetchedValue())
    total_lab_hours = Column(Integer, index=True, server_default=FetchedValue())
    modified_by = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())


t_schema_migrations = Table(
    'schema_migrations', db.metadata,
    Column('version', String(255), nullable=False, unique=True)
)


class Setting(db.Model):
    __tablename__ = 'settings'
    __table_args__ = (
        UniqueConstraint('thing_type', 'thing_id', 'var'),
    )

    id = Column(Integer, primary_key=True)
    var = Column(String(255), nullable=False)
    value = Column(Text)
    thing_id = Column(Integer, server_default=FetchedValue())
    thing_type = Column(String(30), server_default=FetchedValue())
    created_at = Column(DateTime, server_default=FetchedValue())
    updated_at = Column(DateTime, server_default=FetchedValue())


t_sqlite_sequence = Table(
    'sqlite_sequence', db.metadata,
    Column('name', NullType),
    Column('seq', NullType)
)


class Staff(db.Model):
    __tablename__ = 'staff'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), server_default=FetchedValue())
    admin_workload = Column(Float, server_default=FetchedValue())
    research_workload = Column(Float, server_default=FetchedValue())
    full_time_equivalent = Column(Float, server_default=FetchedValue())
    is_new = Column(Integer, server_default=FetchedValue())
    notes = Column(Text)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    buyout = Column(Float, server_default=FetchedValue())
    leave = Column(Float, server_default=FetchedValue())
    discipline_id = Column(Integer, index=True, server_default=FetchedValue())
    year_id = Column(Integer, index=True, server_default=FetchedValue())
    image_url = Column(String(255), server_default=FetchedValue())
    modified_by = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())


class Years(db.Model):
    __tablename__ = 'years'

    id = Column(Integer, primary_key=True)
    number = Column(String(255), server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
        
class CourseStaffLog(db.Model):
    __tablename__ = 'course_staff_log'

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer,db.ForeignKey('courses.id'), index=True,  server_default=FetchedValue())
    staff_id = Column(Integer, db.ForeignKey('staff.id'), index=True, server_default=FetchedValue())
    workload = Column(Float, server_default=FetchedValue())
    is_coordinator = Column(Integer, server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    year_id = Column(Integer, index=True, server_default=FetchedValue())
    nt_hours = Column(Integer, index=True, server_default=FetchedValue())
    modified_by = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    obj_id = Column(Integer, nullable=True)    

    def __repr__(self):
        return '%s' % self.id
                
        
class StaffLog(db.Model):
        __tablename__ = 'staff_log'

        id = Column(Integer, primary_key=True)
        name = Column(String(255), server_default=FetchedValue())
        admin_workload = Column(Float, server_default=FetchedValue())
        research_workload = Column(Float, server_default=FetchedValue())
        full_time_equivalent = Column(Float, server_default=FetchedValue())
        is_new = Column(Integer, server_default=FetchedValue())
        notes = Column(Text)
        created_at = Column(DateTime, nullable=False)
        updated_at = Column(DateTime, nullable=False)
        buyout = Column(Float, server_default=FetchedValue())
        leave = Column(Float, server_default=FetchedValue())
        discipline_id = Column(Integer, index=True, server_default=FetchedValue())
        year_id = Column(Integer, index=True, server_default=FetchedValue())
        image_url = Column(String(255), server_default=FetchedValue())
        modified_by = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())    
        obj_id = Column(Integer, nullable=True)   
        
        def __repr__(self):
            return '%s' % self.id
            
            
class CourseLog(db.Model):
    __tablename__ = 'courses_log'

    id = Column(Integer, primary_key=True)
    code = Column(String(255), server_default=FetchedValue())
    title = Column(Text)
    trimester = Column(String(255), server_default=FetchedValue())
    expected_students = Column(Integer, server_default=FetchedValue())
    is_offered = Column(Integer, server_default=FetchedValue())
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    status = Column(String(255), server_default=FetchedValue())
    student_factor = Column(Float, server_default=FetchedValue())
    course_discipline_id = Column(Integer, server_default=FetchedValue())
    year_id = Column(Integer, index=True, server_default=FetchedValue())
    num_lectures_week = Column(Integer, index=True, server_default=FetchedValue())
    lecture_duration  = Column(Integer, index=True, server_default=FetchedValue())
    total_lab_hours = Column(Integer, index=True, server_default=FetchedValue())
    modified_by = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    obj_id = Column(Integer, nullable=True)  
    
class ModelLog(db.Model):
    __tablename__ = 'model_log'

    id = Column(Integer, primary_key=True)
    equation = Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    low_thresh=Column(Integer)
    hi_thresh = Column(Integer)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    year_id = Column(Integer,  server_default=FetchedValue())
    modified_by= Column(String(255), nullable=False, unique=True, server_default=FetchedValue())
    obj_id = Column(Integer, nullable=True)  
    
    def __repr__(self):
        return '%s' % self.id
        
        
class Role(db.Model):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
   
    staff_id = Column(Integer, nullable=False, server_default=FetchedValue())
    group_id=Column(Integer, nullable=False,  server_default=FetchedValue())
  #  discipline_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    year_id = Column(Integer, server_default=FetchedValue())
    title= Column(String(255), nullable=False, server_default=FetchedValue())
    workload = Column(Float, nullable=False, server_default=FetchedValue())
    level=Column(Integer, nullable=False, server_default=FetchedValue())
    trimester=Column(Integer, nullable=False, server_default=FetchedValue())
    required_group = Column(Integer, nullable=False, server_default=FetchedValue())
    
    def __repr__(self):
        return '%s' % self.id