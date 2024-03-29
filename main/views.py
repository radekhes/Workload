from ecs.dbadmin_auth import AuthModelView
from ecs.umniverse.decorators import appauth_required
from ecs.decorators import login_required, group_required
from flask import Blueprint, request, render_template, redirect, url_for, abort, current_app,jsonify
from sqlalchemy import text
from main import db, adminApp
from datetime import datetime, timedelta
from datetime import date

#Requirements for model imports
from main.models import AdminTable
from main.models import CourseStaff
from main.models import Course
from main.models import Setting
from main.models import Years
from main.models import Staff
from main.models import Discipline
from main.models import Model
from main.models import Role
from main.models import ModelLog
from main.models import CourseLog
from main.models import StaffLog
from main.models import CourseStaffLog
from main.models import Model_Set_Entity

#Flask forms
from flask_wtf import Form
from wtforms import TextField
from main.forms import AssignStaff

from flask import g


#ECS intrinsics
import ecs.umniverse as um

from main import db
from flask_mail import Mail, Message

import json
import re
import math

#SQL ALCHEMY INTEGRATION --UNNEEDED DELETEME
from sqlalchemy import engine
from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy import and_

from collections import deque
main_views = Blueprint('main_views', __name__)
from flask import flash

adminApp.add_view(AuthModelView(AdminTable , db.session))
adminApp.add_view(AuthModelView(CourseStaff, db.session))
adminApp.add_view(AuthModelView(Course, db.session))
adminApp.add_view(AuthModelView(Discipline, db.session))
adminApp.add_view(AuthModelView(Setting, db.session))
adminApp.add_view(AuthModelView(Years, db.session))
adminApp.add_view(AuthModelView(Staff, db.session))
adminApp.add_view(AuthModelView(Model, db.session))
adminApp.add_view(AuthModelView(Role, db.session))
adminApp.add_view(AuthModelView(Model_Set_Entity, db.session))
adminApp.add_view(AuthModelView(StaffLog, db.session))
adminApp.add_view(AuthModelView(ModelLog, db.session))
adminApp.add_view(AuthModelView(CourseStaffLog, db.session))
adminApp.add_view(AuthModelView(CourseLog, db.session))

#import parser
from ecs.dbadmin_auth import  AppView, expose

#NOTE THAT WORKLOAD ADMIN AND RESEARCH WORKLOAD ARE sent as FTE ratios and calculated on the CLient side. MODEL-WORKLOAD is calculated server side. 
DEBUG_INFO=0
COURSE_HOURS_PER_COURSE=150
FTE_HOURS=1725
HI_THRESH=1400
MED_THRESH=1100
LECTURE_LENGTH=50
STORAGE_FRACTION=1000

GENERAL_SELECTION=0
COURSE_SELECTION=4
DISCIPLINE_SELECTION=2
LEVEL_SELECTION=3
DISC_LEVEL_SELECTION=1
debug=0;
             
@main_views.route('/', methods=['GET', 'POST'])
@group_required('ecs')
def root():
    return redirect(url_for('.staff_home'))  # PASS the form to the template renderer...

# Default equation should be -C_BAU
def calc_workload(mod,workload, staff, course, course_staff):
    #S=course.status
    global COURSE_HOURS_PER_COURSE
    global FTE_HOURS
    Course_Hours=COURSE_HOURS_PER_COURSE;
    C_Lev=re.sub(r'\D',"", course.code)[0]      #100=1, 200=2, 300=3, 400=4, 500=5
    C_Lab_Hours = course.total_lab_hours        #Total lab hours of required of course.
    C_Stud_Fact=course.student_factor           #Student factor. 
    C_Exp_Stud=course.expected_students         #Students expected
    C_Status=3 if (course.status=='new') else 2 if (course.status=='revised') else 1 if (course.status=='existing') else 0
    coord=1; #default to true -to compute total course workload.
    S_Lab_Hours=0 #DEFAULT TO 0
    if staff!=-1:
        S_Lab_Hours = course_staff.nt_hours  # Lab hours of staff for given course.
        S_Buy=staff.buyout                          #
        S_FTE=staff.full_time_equivalent
        S_New=staff.is_new
        S_Research=staff.research_workload          #research*FTE
        S_Admin = staff.admin_workload              #admin*FTE
        coord = course_staff.is_coordinator;

    W=workload;
    work=0;
    work2=0;

    try:
        work=eval(mod.equation);
        work2=eval(str(work)+'*(W*0.8 + coord*0.2) + S_Lab_Hours');

    except Exception as e:
        work=1;
    
    return work2

#SELECTION 0=General, 2=Discipline, 3=Lev,  1=Disc+level, 4=Course,
def get_model(course, model_set_name, debug=False):

    mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == model_set_name, Model_Set_Entity.specific_field==course.id, Model_Set_Entity.selection==COURSE_SELECTION).first();
    if not mod:
        mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == model_set_name, Model_Set_Entity.specific_field ==   str(course.course_discipline_id) +course.code[4] , Model_Set_Entity.selection == DISC_LEVEL_SELECTION ).first();
        if not mod:
            mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == model_set_name,
                                                    Model_Set_Entity.specific_field == course.course_discipline_id,
                                                    Model_Set_Entity.selection == DISCIPLINE_SELECTION).first();
 
            if not mod:
                mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == model_set_name,
                                                        Model_Set_Entity.specific_field == course.code[4]+'00' ,
                                                        Model_Set_Entity.selection == LEVEL_SELECTION).first();
                    
                if not mod:
                    mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == model_set_name, Model_Set_Entity.selection == GENERAL_SELECTION).order_by(Model_Set_Entity.id.desc()).first();
                    
                    if not mod:
                        mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == 'default', Model_Set_Entity.selection == GENERAL_SELECTION).first();
                    #elif debug==True:   #FOR DEBUGGING PURPOSES ONLY
                #    return 'true';
   #mod=Model.query.filter(Model.id==mod.model_id).first();
    mod=Model.query.filter(Model.id==mod.model_id).order_by(Model.id.desc()).first();
    return mod

@main_views.route('/staff', methods=['GET', 'POST'])
@group_required('ecs')
def staff_home(VIEW_STAFF=-1,YEAR=-1, VIEW_COURSE=-1, Model_set_name='default',error_msg=''):
    year=request.args.get('year')
    staff_dict={}

    VIEW_COURSE_TRIMESTER=-1

    if not year:
        year = date.today().year

    if YEAR!=-1:
        year=YEAR

    year_db = Years.query.filter(Years.number == year).first()
    staff_set = Staff.query.filter(Staff.year_id == year_db.id).all()

    for sm in staff_set:
        staff_dict[sm.name]=sm

    discipline_set = Discipline.query.filter().all()     

    #STAFF DATASTRUCTURES...
    group_workload_sum={}       #group_set [disc][staff][trimester] workload
    group_set={}                #group_set [disc][staff][trimester] coursename
    group_course_staff_set={}   #group_set [disc][staff][trimester] course_staff objects

    #STAFF MODEL BASED
    model_group_workload_sum = {}  # group_set [disc][staff][trimester] workload

    #COURSE DATASTRUCTURES...
    course_set = {}                  #course_set[str(disc.name)][str(staff.name)]['1'] cs
    course_group_course_set = {}     #[str(disc.name)][tri][level][str(c.code)]['lect'] = workload (individual);
    course_group_workload_sum = {}   #[str(disc.name)][tri][level][str(c.code)]['lect'] = sum

    mod_set = Model_Set_Entity.query.filter( Model_Set_Entity.name==Model_set_name).all();
    
    complete_mod_entity_set = Model_Set_Entity.query.filter( 1 == 1 ).all();
    complete_mod_entity_set_names=[str(x.name) for x in complete_mod_entity_set]
    unique_model_entity_set_names=[];
    [unique_model_entity_set_names.append(str(x)) for x in complete_mod_entity_set_names if str(x) not in unique_model_entity_set_names] #Get all distinct models_set_entitues
        
    mod = Model.query.filter(Model.name == 'default', Model.year_id ==year_db.number  ).first();
    model_map={}
    model_desc={}
    model_type={}
    model_type_details={}
    model_thresh={}

    for mes in complete_mod_entity_set:
        model_map[mes.name]=[];
        model_type[mes.name]={}
        model_desc[mes.name]={}
        model_type_details[mes.name]={}
        model_thresh[mes.name] = {}
        model_thresh[mes.name]['low_thresh']=mes.low_thresh/STORAGE_FRACTION
        model_thresh[mes.name]['hi_thresh'] = mes.hi_thresh/STORAGE_FRACTION

    for mes in complete_mod_entity_set:
        my_mod = Model.query.filter(Model.id == mes.model_id).first();
        
        model_desc[mes.name][my_mod.name]=[];   
        model_type[mes.name][my_mod.name]=[];
        model_type_details[mes.name][my_mod.name]=[];

        model_map[mes.name].append(my_mod.name);
        model_desc[mes.name][my_mod.name].append(my_mod.equation);
        model_type[mes.name][my_mod.name]= "Course" if mes.selection==4 else "General" if mes.selection==0 else "Discipline" if mes.selection==2 else "Level" if mes.selection==3 else "Disc_level"
        if mes.selection==4:
            #Find the related course.
            c1=Course.query.filter(Course.id==mes.specific_field).first();
            model_type_details[mes.name][my_mod.name]=c1.code;
        elif mes.selection==3:
            model_type_details[mes.name][my_mod.name]=mes.specific_field;
        elif mes.selection==2:
            c1=Discipline.query.filter(Discipline.id==mes.specific_field).first();
            model_type_details[mes.name][my_mod.name]=c1.name;        
        elif mes.selection==1:
            d1=Discipline.query.filter(Discipline.id==mes.specific_field[:len(mes.specific_field)-1]).first();
            model_type_details[mes.name][my_mod.name]=d1.name +mes.specific_field[len(mes.specific_field)]+"0"+"0";    
        else:
            model_type_details[mes.name][my_mod.name]=0 

    for disc in discipline_set:
        staff_set2=Staff.query.filter(Staff.discipline_id == disc.id, Staff.year_id==year_db.id).all()

        group_set[str(disc.name)] = {}
        group_course_staff_set[str(disc.name)] = {}
        group_workload_sum[str(disc.name)] = {}
        
        model_group_workload_sum[str(disc.name)] = {}
                    
        # BEGIN COURSES DS.
        course_set[str(disc.name)] = {}
        course_group_course_set[str(disc.name)] = {}
        course_group_workload_sum[str(disc.name)] = {}

        for s in staff_set2:
            cs_set=CourseStaff.query.filter(CourseStaff.staff_id==s.id,CourseStaff.year_id==year_db.id).all()
            group_set[str(disc.name)][str(s.name)]={}
            group_set[str(disc.name)][str(s.name)]['1']=[]
            group_set[str(disc.name)][str(s.name)]['2'] = []
            group_set[str(disc.name)][str(s.name)]['3'] = []

            group_course_staff_set[str(str(disc.name))][str(s.name)]={}
            group_course_staff_set[str(disc.name)][str(s.name)]['1']=[]
            group_course_staff_set[str(disc.name)][str(s.name)]['2'] = []
            group_course_staff_set[str(disc.name)][str(s.name)]['3'] = []

            if s.is_new==1:
                group_course_staff_set[str(disc.name)][str(s.name)]['New'] = 'New';
            else:
                group_course_staff_set[str(disc.name)][str(s.name)]['New'] = 0;
            group_course_staff_set[str(disc.name)][str(s.name)]['Id'] = s.id;

            group_workload_sum[str(disc.name)][str(s.name)] = {}
            group_workload_sum[str(disc.name)][str(s.name)]['1']=0
            group_workload_sum[str(disc.name)][str(s.name)]['2'] = 0
            group_workload_sum[str(disc.name)][str(s.name)]['3'] = 0
            
            group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = 0;
            group_workload_sum[str(disc.name)][str(s.name)]['Total_General'] = s.research_workload + s.admin_workload;
            group_workload_sum[str(disc.name)][str(s.name)]['Research'] = s.research_workload;
            group_workload_sum[str(disc.name)][str(s.name)]['Admin'] = s.admin_workload;

            #model based...
            model_group_workload_sum[str(disc.name)][str(s.name)] = {}
            model_group_workload_sum[str(disc.name)][str(s.name)]['1'] = 0
            model_group_workload_sum[str(disc.name)][str(s.name)]['2'] = 0
            model_group_workload_sum[str(disc.name)][str(s.name)]['3'] = 0
            model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = 0;
            model_group_workload_sum[str(disc.name)][str(s.name)]['Total_General'] = s.research_workload + s.admin_workload;
            model_group_workload_sum[str(disc.name)][str(s.name)]['Research'] = s.research_workload;
            model_group_workload_sum[str(disc.name)][str(s.name)]['Admin'] = s.admin_workload;
                
            for cs in cs_set:
                c = Course.query.filter(Course.id == cs.course_id).first()

                if c.trimester=='F':
                    group_course_staff_set[str(disc.name)][str(s.name)]['1'].append(float(cs.workload/2))
                    group_course_staff_set[str(disc.name)][str(s.name)]['2'].append(float(cs.workload/2))
                    group_set[str(disc.name)][str(s.name)]['1'].append(c.code)
                    group_set[str(disc.name)][str(s.name)]['2'].append(c.code)

                    group_workload_sum[str(disc.name)][str(s.name)]['1'] = group_workload_sum[str(disc.name)][str(s.name)]['1'] +  float(cs.workload/2) #int(cs.workload/2)  #calc_workload(mod,cs.workload/2, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent);    #//int(cs.workload/2)       #(workload,students=0,new_staff=0,stud_fact=0,level=0, num_courses=0,buyout=0, fte=0): //calculate_workload #//
                    group_workload_sum[str(disc.name)][str(s.name)]['2'] = group_workload_sum[str(disc.name)][str(s.name)]['2'] +  float(cs.workload/2) # calc_workload(mod,cs.workload/2, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//       #//
                    group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] + float(cs.workload)

                    #MODEL BASED
                    model_group_workload_sum[str(disc.name)][str(s.name)]['1'] = model_group_workload_sum[str(disc.name)][str(s.name)]['1'] + calc_workload(get_model(c,Model_set_name),cs.workload / 2, s, c, cs)  # int(cs.workload/2)  #calc_workload(get_model(c,Model,cs.workload/2, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent);    #//int(cs.workload/2)       #(workload,students=0,new_staff=0,stud_fact=0,level=0, num_courses=0,buyout=0, fte=0): //calculate_workload #//
                    model_group_workload_sum[str(disc.name)][str(s.name)]['2'] = model_group_workload_sum[str(disc.name)][str(s.name)]['2'] + calc_workload(get_model(c,Model_set_name),cs.workload / 2, s, c, cs)  # int(cs.workload/2) # calc_workload(get_model(c,Model,cs.workload/2, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//       #//
                    model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] + calc_workload(get_model(c,Model_set_name),cs.workload , s, c, cs)  # cs.workload #calc_workload(get_model(c,Model,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//     #//

                else:
                    group_course_staff_set[str(disc.name)][str(s.name)][str(c.trimester)].append(float(cs.workload))
                    group_set[str(disc.name)][str(s.name)][str(c.trimester)].append(str(c.code))

                    group_workload_sum[str(disc.name)][str(s.name)][str(c.trimester)] =group_workload_sum[str(disc.name)][str(s.name)][str(c.trimester)]+ float(cs.workload) #calc_workload(get_model(c,Model,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #cs.workload    #//
                    group_workload_sum[str(disc.name)][str(s.name)][ 'Total_Courses'] = group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] +float(cs.workload) #cs.workload #calc_workload(get_model(c,Model,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); # cs.workload                   #//

                    model_group_workload_sum[str(disc.name)][str(s.name)][str(c.trimester)] = model_group_workload_sum[str(disc.name)][str(s.name)][str(c.trimester)] + calc_workload(get_model(c,Model_set_name),cs.workload , s, c,cs) #   model_group_workload_sum[str(disc.name)][str(s.name)]['Total'] = \
                    model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] + calc_workload(get_model(c,Model_set_name),cs.workload , s, c, cs)  # cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//     #//

   # Find all courses within a discipline...  1st find all staff of dicipline(already done...), then find each coursestaff then find course...    THIS IS OLD METHODS.
   # for s in staff_set2:
   #     cs_set = CourseStaff.query.filter(CourseStaff.staff_id == s.id, CourseStaff.year_id == year_db.id).all()
   #     for  stmt2 = text('SELECT TEAM.TEAM_ID FROM team_signup.TEAM join TEAM_MEMBER on TEAM.TEAM_ID = TEAM_MEMBER.TEAM_ID WHERE TEAM.ASSIGNMENT_ID=:ass_id and TEAM_MEMBER.USERNAME=:user')  #
        #
    for disc in discipline_set:

        for tri in ['1','2','3','F']:
            course_set[str(disc.name)][tri] = {}
            course_group_course_set[str(disc.name)][tri] = {}
            course_group_workload_sum[str(disc.name)][tri] = {}

            #JUST INITIALISE SOME VARIABLES THE LEVEL IS DERIVED FROM THE COURSECODE...
            for level in ['100', '200','300','400','500']:
                course_set[str(disc.name)][tri][level] = {}
                course_group_course_set[str(disc.name)][tri][level] = {}
                course_group_workload_sum[str(disc.name)][tri][level] = {}

            #NOTE WE WILL NOT INFER THE DISCILPINE FROM THE LECTURERS "CONVENTIONAL DISCIPLINE" BUT FROM THE COURSE COURSE_DISCIPLINE....
            course_set2 = Course.query.filter(Course.year_id == year_db.id, Course.trimester == tri, Course.course_discipline_id==disc.id).all()

            for ct in course_set2:
                match = re.match(r"([a-z]+)([0-9]+)([a-z]*)", ct.code, re.I)
                if match:
                    items = match.groups()
                    level=str(items[1])
                else:
                    continue
                try:
                    course_set2.remove(items[0]+str(items[1])+str(items[2]))
                except:
                    STUB=1

                level=level[0]+"0"+"0"

                course_set[str(str(disc.name))][tri][level][str(ct.code)] = {}
                course_set[str(disc.name)][tri][level][str(ct.code)]['lect'] = {}
                course_set[str(disc.name)][tri][level][str(ct.code)]['coord'] ='None';
                course_set[str(disc.name)][tri][level][str(ct.code)]['sum'] = 0;
                course_set[str(disc.name)][tri][level][str(ct.code)]['students'] = 0;
                course_set[str(disc.name)][tri][level][str(ct.code)]['title'] = str(ct.title);
                course_set[str(disc.name)][tri][level][str(ct.code)]['lecture_duration'] = str(ct.lecture_duration);
                course_set[str(disc.name)][tri][level][str(ct.code)]['num_lectures_week'] = str(ct.num_lectures_week);
                course_set[str(disc.name)][tri][level][str(ct.code)]['is_offered'] = str(ct.is_offered);
                course_set[str(disc.name)][tri][level][str(ct.code)]['total_lab_hours'] = str(ct.total_lab_hours);

                course_group_course_set[str(disc.name)][tri][level][str(ct.code)] = {}
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['lect'] = {};
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['coord'] ='None';
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['tutors'] = 'None';
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['sum'] = 0;
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['students'] = int(ct.expected_students);
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['stud_fact'] = int(ct.student_factor);
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['status'] = ct.status;
                course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['work_total'] = calc_workload(get_model(ct,Model_set_name),1, -1, ct, -1);

                course_group_workload_sum[str(disc.name)][tri][level][str(ct.code)] = 0

                cs_set = CourseStaff.query.filter(CourseStaff.course_id == ct.id,
                                                  CourseStaff.year_id == year_db.id).all()

                for cs in cs_set:
                             s = Staff.query.filter(Staff.id == cs.staff_id).first()
                             if cs.is_coordinator == 1:
                                   course_set[str(disc.name)][tri][level][str(ct.code)]['coord']=str(s.name)
                                   course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['coord']=str(s.name);
                                   course_set[str(disc.name)][tri][level][str(ct.code)]['lect'][str(s.name)] = cs.workload#calc_workload(mod,cs.workload,s,ct, cs) #cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #cs.workload;                                            #//
                                   course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['lect'][str(s.name)] = cs.workload#calc_workload(mod,cs.workload,s,ct, cs) # cs.workload # calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #cs.workload;                               #//
                             else:
                                   course_set[str(disc.name)][tri][level][str(ct.code)]['lect'][str(s.name)]=cs.workload#calc_workload(mod,cs.workload,s,ct, cs)#cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #cs.workload;                                                 #//
                                   course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['lect'][str(s.name)]=cs;

                             course_set[str(disc.name)][tri][level][str(ct.code)]['sum']=course_set[str(disc.name)][tri][level][str(ct.code)]['sum']+cs.workload#calc_workload(mod,cs.workload,s,ct, cs)#cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.fill_time_equivalent); #cs.workload;                    #//
                             course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['sum'] = course_group_course_set[str(disc.name)][tri][level][str(ct.code)]['sum'] +cs.workload#calc_workload(mod,cs.workload,s,ct, cs)#cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #cs.workload;   #//
                             course_group_workload_sum[str(disc.name)][tri][level][str(ct.code)] = course_group_workload_sum[str(disc.name)][tri][level][str(ct.code)] +cs.workload#calc_workload(mod,cs.workload,s,ct, cs)#cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #cs.workload;              #//

#MAKING DICTIONARY SPARSE...
            for level in ['100', '200','300','400','500']:
                if course_set[str(disc.name)][tri][level] == {}:
                    del course_set[str(disc.name)][tri][level]

            course_set={k: v for k, v in course_set.items() if v is not None}
#MAKING DICTIONARY SPARSE...
        for tri in ['1','2','3','F']:
            if course_set[str(disc.name)][tri] == {}:
                del course_set[str(disc.name)][tri]

    trimester_set=['1','2','3','F']
    level_set=['100','200','300','400','500']

    current_app.logger.debug("course_set:   ")
    current_app.logger.debug(course_set)
    
    ############################################
    #Adding Specialty Roles. 
    ############################################
    roles = Role.query.filter(Role.year_id == year_db.id).all()
    all_staff=Staff.query.filter(Staff.year_id==year_db.id).all()
    role_map={};
    role_map['Total']=0
    role_weights={};
    tri_set_prim=['1','2','3','F']
    role_set={};
    staff_role={};
   # debug=[];
    
    for stf in all_staff: 
        staff_role[stf.name]={};
        staff_role[stf.name]['Total']=0;
        
    for disc in discipline_set:
           role_set[disc.name]={};
           role_set[disc.name]['Total']=0
           for tri in tri_set_prim:
               role_set[disc.name][tri]={}
               role_set[disc.name][tri]['Total']=0
               for lev in level_set:
                   role_set[disc.name][tri][lev]={} #just initiate all...
                   role_set[disc.name][tri][lev]['Total']=0

    for role in roles:
         stf=Staff.query.filter(Staff.id==role.staff_id, Staff.year_id==year_db.id).first()
         if not stf:
             role_map[role.title]="";
         else:
             group="Discipline" if role.required_group==0 else "Level" if role.required_group==1 else "School";
             tri= 'F' if role.trimester==3 else str(role.trimester+1)
             role_map[role.title]=stf.name;
             staff_role[stf.name]['Total']=staff_role[stf.name]['Total']+role.workload;
             staff_role[stf.name][role.title]=role.workload;
             role_weights[role.title]=role.workload;       
                
             if group=='Discipline':
                disc=Discipline.query.filter(Discipline.id==role.group_id ).first();
                disc=disc.name;
                role_set[disc]['Total']=role_set[disc]['Total']+role.workload;
                for tri_i in tri_set_prim:
                        if tri_i==tri:
                            role_set[disc][tri_i]['Total']=role_set[disc][tri_i]['Total']+role.workload;
                            for lev in level_set:
                                 role_set[disc][tri_i][lev]['Total']=role_set[disc][tri_i][lev]['Total']+role.workload
                                 role_set[disc][tri_i][lev][role.title]=role.workload;
             elif group=='Level':
                lev=str(role.level);
                for disc in discipline_set:
                    disc=disc.name
                    for tri_i in tri_set_prim:
                            if tri_i==tri:
                                role_set[disc][tri_i]['Total']=role_set[disc][tri_i]['Total']+role.workload;
                                role_set[disc][tri_i][lev]['Total']=role_set[disc][tri_i][lev]['Total']+role.workload
                                role_set[disc][tri_i][lev][role.title]=role.workload; 

             elif group=='School':
               for disc in discipline_set:
                    disc=disc.name
                    size_disc=len(discipline_set);
                    for tri_i in tri_set_prim:
                            if tri_i==tri:
                                role_set[disc][tri_i]['Total']=role_set[disc][tri_i]['Total']+role.workload;
                                role_set[disc][tri_i][lev][role.title]=role.workload; 
                                for lev in level_set:
                                    role_set[disc][tri_i][lev]['Total']=role_set[disc][tri_i][lev]['Total']+role.workload
                                    role_set[disc][tri_i][lev][role.title]=role.workload; 

    year_set = [y_i.number for y_i in Years.query.filter().order_by(Years.number.desc())]

    #BUILD COURSE-DISCIPLINE MAP
    CD_Map={}

    for disc in discipline_set:
        CD_Map[disc.name] = []
        c_s = Course.query.filter(Course.year_id == year_db.id, Course.course_discipline_id == disc.id).all();
        for c in c_s:
            CD_Map[disc.name].append(c.code)

    staff_discipline=-1
    if VIEW_STAFF!=-1:
        year_db = Years.query.filter(Years.number == year).first()
        staff_mem=Staff.query.filter(Staff.name==VIEW_STAFF, Staff.year_id==year_db.id).first();
        staff_discipline=Discipline.query.filter(staff_mem.discipline_id==Discipline.id).first();
        staff_discipline=staff_discipline.name

    if VIEW_COURSE != -1:
        year_db = Years.query.filter(Years.number == year).first()
        view_course = Course.query.filter(Course.code == VIEW_COURSE, Course.year_id == year_db.id).first();
        VIEW_COURSE_TRIMESTER = view_course.trimester

    return render_template('home.html', FTE_HOURS=FTE_HOURS, COURSE_HOURS=COURSE_HOURS_PER_COURSE, COURSE_HOURS_PER_COURSE=COURSE_HOURS_PER_COURSE,HI_THRESH=HI_THRESH, MED_THRESH=MED_THRESH, CourseDisc_Map=CD_Map,model_set_name=Model_set_name, model_description=model_desc, model_thresh=model_thresh,complete_model_set = unique_model_entity_set_names, model_map=model_map, model_set= unique_model_entity_set_names, model_type_details=model_type_details, model_type=model_type, debug=debug, role_map=role_map, role_weights=role_weights, role_set=role_set,staff_role=staff_role,all_years=year_set,hi_thresh=HI_THRESH, low_thresh=MED_THRESH, model=mod, model_group_workload=model_group_workload_sum, VIEW_STAFF=VIEW_STAFF, staff_member_discipline=staff_discipline, VIEW_COURSE_TRIMESTER=VIEW_COURSE_TRIMESTER, VIEW_COURSE=VIEW_COURSE, level_set=level_set, trimester_set=trimester_set, course_group_workload_sum=course_group_workload_sum, course_group_course_set=course_group_course_set, course_set=course_set, group_workload=group_workload_sum, group_course_set=group_course_staff_set, year=year_db, staff_set=staff_set, staff_dict=staff_dict, discipline_set=discipline_set, group_set=group_set, error=error_msg)  # PASS the form to the template renderer...


@main_views.route('/admin_view_staff', methods=['POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_view_staff():

    year = request.form['year']
    c_name = request.form["staff_name"]
   # current_app.logger.debug("This is the name:   "+year +' sfd')
    t=re.sub('_',' ',c_name )
   # current_app.logger.debug("This is the name:   " + t)
    role_str="";
    cur_model = request.form['cur_model'];
    
    if year:
        year_db = Years.query.filter(Years.number == year).first()
        current_app.logger.debug("MODEL:   " + str(year_db.id))
        staff = Staff.query.filter(Staff.year_id == year_db.id, Staff.name==str(t.title())).first()
        roles = Role.query.filter(Role.year_id == year_db.id, Role.staff_id==staff.id ).all()
        if roles:
            for role_i in range(0,len(roles)):
                role_str=role_str+roles[role_i].title +' ('+ str(roles[role_i].workload)+' FTE) ;'
            
        disc=Discipline.query.filter( Discipline.id==staff.discipline_id ).first()

        base_mod = Model_Set_Entity.query.filter( Model_Set_Entity.name == 'default').first();
        if not base_mod:
         current_app.logger.error("This is no base_mod")
         return jsonify({'status': 'ERR'});

        #base_mod=Model.query.filter(year_db.id == Model.year_id,Model.name=='default').first();
       # if not base_mod:
       #     current_app.logger.error("This is no base_mod")get_model(course, model_set_name, debug=False)
       #     return jsonify({'status': 'ERR'});

        mod = Model_Set_Entity.query.filter( Model_Set_Entity.name == cur_model).first();
        if not mod:
         current_app.logger.error("This is no mod")
         return jsonify({'status': 'ERR'});
        #mod=Model.query.filter(year_db.id == Model.year_id, Model.name == cur_model ).first();
        #if not mod:
        #    current_app.logger.error("This is no mod")
        #    return jsonify({'status': 'ERR'});

        cs_set = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, staff.id == CourseStaff.staff_id).all()
        user_model={};
        base_model_workload={};
        nt_hours={}
        for cs in cs_set:
            c = Course.query.filter(Course.year_id == year_db.id, cs.course_id == Course.id).first()
            user_model[c.code]=calc_workload(get_model(c, mod.name, debug=False),cs.workload,staff,c,cs) #(mod,workload, staff, course, course_staff):get_model(course, model_set_name, debug=False)
            base_model_workload[c.code] = calc_workload( get_model(c, base_mod.name, debug=False), cs.workload, staff, c, cs);
            nt_hours[c.code]=cs.nt_hours

        return jsonify({'status': 'OK', 'img_link': staff.image_url, 'staff_name': staff.name, 'roles': role_str ,'discipline': disc.name, "notes": staff.notes, 'FTE': staff.full_time_equivalent, 'buyout': staff.buyout, 'work':base_model_workload, 'model_work':  user_model, 'nt_hours': nt_hours , 'leave': staff.leave, 'research': str(staff.research_workload), 'admin':str(staff.admin_workload) });
    return jsonify({'status': 'ERR' });


@main_views.route('/admin_assign_course_staff', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_assign_course_staff():
    year = request.args.get('year')
    staff_name = request.args.get("staff_name")
    course_name = request.args.get("course_name")
    staff_name_clean=re.sub('_',' ',staff_name )
    workload=float(request.args.get("workload"))
    coord=request.args.get("coord")
    nt_hours = float(request.args.get("nt_hours"))
    if coord=="on":
       coord=1
    else:
       coord=0 
    course_name = re.sub('[\']', '', course_name)
    #id = Column(Integer, primary_key=True)
   # workload_new_mem=0;

    if year:
        year_db = Years.query.filter(Years.number == year).first()
        staff = Staff.query.filter(Staff.year_id == year_db.id, Staff.name==staff_name_clean).first()
        disc=Discipline.query.filter( Discipline.id==staff.discipline_id ).first()
        course=Course.query.filter(Course.year_id==year_db.id, Course.code==course_name).first()
        #course_staff=CourseStaff.query.filter(CourseStaff.course_id==course.id,CourseStaff.staff_id==staff.id, CourseStaff.year==year_db.id).first();
        cs_orig = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id, CourseStaff.staff_id == staff.id).first()  # IF COURSE_STAFF ALREADY EXISTS
        if not cs_orig:
            cs_orig=CourseStaff(course.id,staff.id,float(workload),coord,year_db.id, nt_hours, g.username);
            #test_1=0;
            workload_new_mem=workload
        else:
            workload_new_mem = workload - cs_orig.workload;
       # cs_orig=CourseStaff.query.filter(CourseStaff.year_id==year_db.id, CourseStaff.course_id==course.id, CourseStaff.staff_id==staff.id).first()       #IF COURSE_STAFF ALREADY EXISTS
        cs_set = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id ).all()  # IF COURSE_STAFF ALREADY EXISTS
        num_cs=len(cs_set)
        total_work=float(workload_new_mem)
        for cs in cs_set:
             if cs.id!=cs_orig.id:
                total_work=total_work+cs.workload

        if total_work>1:
            return staff_home(VIEW_COURSE=course_name, YEAR=year_db.number, error_msg='Assignment not updated: Error total work must be less than or equal to 1.')

        if cs_orig:
           if (cs_orig.is_coordinator!=coord and coord==1):
              #then turn off all other staff members coordinator roles... 
              #cs_orig_set=CourseStaff.query.filter(CourseStaff.year_id==year_db.id, CourseStaff.course_id==course.id).all()
              for cs in CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id).all():
                  cs.is_coordinator=0
                  db.session.add(cs)
              cs_orig.is_coordinator=1

           elif cs_orig.is_coordinator!=coord and coord==0:
               cs_orig.is_coordinator=0

           db.session.add(cs_orig)

        else:
            current_app.logger.error("ERROR");
        #     db.session.add(course_staff)

        db.session.commit()
        return staff_home(VIEW_STAFF=staff_name_clean, YEAR=year_db.number ,error_msg='')

    return jsonify({'status': 'ERR' });




@main_views.route('/admin_edit_course_staff', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_edit_course_staff():
    #current_app.logger.debug("This is the current name:")
    year = request.args.get('year')
    staff_name = request.args.get("staff_name")
    course_name = request.args.get("course_name")
    staff_name_clean=re.sub('_',' ',staff_name )
    workload=float(request.args.get("workload"))
    nt_hours = float(request.args.get("nt_hours"))
    coord=0
    if request.args.get("coord"):
        coord=1        
        
    course_name = re.sub('[\']', '', course_name)
    current_app.logger.error("ERROR");

    if year:
        year_db = Years.query.filter(Years.number == year).first()
        staff = Staff.query.filter(Staff.year_id == year_db.id, Staff.name==staff_name_clean).first()
        disc=Discipline.query.filter( Discipline.id==staff.discipline_id ).first()

        course = Course.query.filter(Course.year_id == year_db.id, Course.code == course_name).first()
        course_staff = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id, CourseStaff.staff_id==staff.id).first()
        #Ensure the edited workload falls =< 1.
        total_work=0;
        cs_set = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id).all()
        workload_test=workload

        for cs in cs_set:
            if course_staff:
                #current_app.logger.error("COURSE_STAFF:"+str(cs.id )+ " "+ str(course_staff.id));
                if cs.id != course_staff.id:
                   #   current_app.logger.error("INSIDE CURRENT COURSE_STAFF:"+str(cs.id) + " W: "+str(cs.workload));
                      workload_test=workload_test+cs.workload
            else:
                workload_test = workload_test + course_staff.workload

    #    current_app.logger.error("WORKLOAD="+str(workload_test));
        if workload_test>1:
            return staff_home(VIEW_STAFF=staff_name, YEAR=year_db.number, error_msg='Assignment not updated: Error total work must be less than or equal to 1.')

        course_staff.workload=float(workload)/1
        course_staff.nt_hours = float(nt_hours) / 1
        course_staff.modified_by = g.username;

        if (course_staff.is_coordinator!=coord and coord==1):
              #then turn off all other staff members coordinator roles...
              cs_orig_set=CourseStaff.query.filter(CourseStaff.year_id==year_db.id, CourseStaff.course_id==course.id).all()
              for cs in cs_orig_set:
                  cs.is_coordinator = 0;
                  db.session.add(cs)
              course_staff.is_coordinator=1
              current_app.logger.error("COORD=1");

        elif course_staff.is_coordinator!=coord and coord==0:
               course_staff.is_coordinator=0
               current_app.logger.error("COORD=0:");

        db.session.add(course_staff)
        db.session.commit()

        return staff_home(VIEW_STAFF=staff_name,YEAR=year_db.number, VIEW_COURSE=-1)

    return jsonify({'status': 'ERR' });


@main_views.route('/admin_edit_course_staff_details', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_edit_course_staff_details():
    #current_app.logger.debug("This is the current name:")
    year = request.args.get('year')
    staff_name = request.args.get("staff_name")
    staff_name_clean=re.sub('_',' ',staff_name )
    notes=request.args.get("notes")
    buyout = request.args.get("buyout")
    fte = request.args.get("fte")
    leave = request.args.get("leave")
    role=request.args.get("role")

    if year:
        year_db = Years.query.filter(Years.number == year).first()
        staff = Staff.query.filter(Staff.year_id == year_db.id, Staff.name==staff_name_clean).first()

        if notes and notes!="" :
           staff.notes=notes;
        if buyout and buyout != "":
           staff.buyout=buyout;
        if leave and leave != "":
           staff.leave=leave;
        if fte and fte != "":
           staff.fte=fte;
           
        if role!="None":
           cur_roles=Role.query.filter(Role.year_id == year_db.id, Role.title == role ).first()          
           cur_roles.staff_id=staff.id;
           db.session.add(cur_roles)
        else:
            cur_role=Role.query.filter(Role.year_id == year_db.id, Role.staff_id == staff.id ).first()          
            if cur_role:
               cur_role.staff_id=staff.id;           
               db.session.add(cur_role)

        staff.modified_by = g.username;
        db.session.add(staff)
        db.session.commit()

        return staff_home(VIEW_STAFF=staff_name_clean,YEAR=year_db.number, VIEW_COURSE=-1)

    return jsonify({'status': 'ERR' });

@main_views.route('/admin_del_course_staff', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_del_course_staff():
    year = request.args.get('year')
    staff_name = request.args.get("staff_name")
    course_name = request.args.get("course_name")
    staff_name_clean=re.sub('_',' ',staff_name )
    course_name = re.sub('[\']', '', course_name)

    if year:
        year_db = Years.query.filter(Years.number == year).first()
        staff = Staff.query.filter(Staff.year_id == year_db.id, Staff.name==staff_name_clean).first()
        disc=Discipline.query.filter( Discipline.id==staff.discipline_id ).first()
        course = Course.query.filter(Course.year_id == year_db.id, Course.code == course_name).first()
        course_staff = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id, CourseStaff.staff_id==staff.id ).first()

        if course_name == "Admin":
            staff.admin_workload = 0;
            staff.modified_by = g.username;
            db.session.add(staff)
        elif course_name == "Research":
            staff.research_workload = 0;
            staff.modified_by = g.username;
            db.session.add(staff)
        else:
            db.session.delete(course_staff)
        db.session.commit()
        return staff_home(VIEW_STAFF=staff_name_clean,YEAR=year_db.number)

    return jsonify({'status': 'ERR' });



@main_views.route('/admin_view_course', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_view_course():

    year = request.form['year']
    c_name = request.form["course_name"]
    t=c_name#re.sub('_',' ',c_name )
    coord='None'

    staff_list = []
    staff_load = []
    staff_lab_hours=[]
    if year:
        year_db = Years.query.filter(Years.number == year).first()
        course = Course.query.filter(Course.year_id == year_db.id, Course.code==str(t)).first()
        course_staff = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id).all()
        for cs in course_staff:
            s=Staff.query.filter(Staff.year_id == year_db.id, Staff.id==cs.staff_id ).first()
            staff_list.append(s.name)
            staff_load.append(cs.workload)
            staff_lab_hours.append(cs.nt_hours)
            if cs.is_coordinator==1:
               coord=s.name

        return jsonify({'status': 'OK', 'course_name': course.code, "title": course.title, "lectures_week":course.num_lectures_week, "total_lab_hours": course.total_lab_hours,  "nt_hours":staff_lab_hours, "duration":course.lecture_duration ,'student_factor': course.student_factor, 'course_status': course.status ,'students': course.expected_students, 'lecturers': staff_list, 'tri':course.trimester, 'coord': coord});

@main_views.route('/admin_assign_course', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_assign_course():

    year = request.form['year']
    c_name = request.form["course_name"]
    s_name = request.form["staff_name"].strip("'")

    workload = float(request.form["workload"])/1
    nt_hours = float(request.form["nt_hours"])
    coord=0
    total_work=0
    current_app.logger.error("NON TEACHING " + str(nt_hours));

    if "coord" in request.form:
            coord = 1

    staff_list = []
    staff_load = []
    staff_list_s=[]
    if year:
        year_db = Years.query.filter(Years.number == year).first()
        course = Course.query.filter(Course.year_id == year_db.id, Course.code==str(c_name)).first()
        staff=Staff.query.filter(Staff.year_id == year_db.id, Staff.name == s_name).first()
        course_staff = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id).all()

        for cs in course_staff:
            total_work=total_work+cs.workload
            cur_staff = Staff.query.filter(Staff.year_id == year_db.id, Staff.id == cs.staff_id).first()
            staff_list.append(cur_staff.name)

        if total_work+workload>1:
            return staff_home(VIEW_STAFF=s_name, YEAR=year_db.number, error_msg='Assignment not updated: Error total work must be less than or equal to 1.')

        if not s_name in staff_list:
            new_course_staff=CourseStaff(course.id,staff.id,workload,int(coord),year_db.id,nt_hours, g.username)

            #TURN OFF ALL OTHER COORDINATORS
            if coord==1:
                for cs in course_staff:
                    cs.is_coordinator = 0;
                    db.session.add(cs)

            db.session.add(new_course_staff)
            db.session.commit()
        else:
            current_app.logger.error("This STAFF MEMEBER HAS ALREADY BEEN ASSIGNED TO THE BLOCK " + str(staff.id));

        return staff_home(VIEW_STAFF=-1,YEAR=year_db.number, VIEW_COURSE=c_name)


@main_views.route('/admin_edit_course', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_edit_course():

    year = request.form['year']
    c_name = request.form["course_name"]
    s_name = request.form["staff_name"].strip("'")
    workload = float(request.form["workload"])/1
    nt_hours = float(request.form["nt_hours"]) / 1
    coord=0
    if "coord" in request.form:
        coord = 1

    staff_list = []
    staff_load = []
    if year:
        year_db = Years.query.filter(Years.number == year).first()
        course = Course.query.filter(Course.year_id == year_db.id, Course.code==str(c_name)).first()
        s=Staff.query.filter(Staff.year_id == year_db.id, Staff.name==s_name ).first()
        course_staff = CourseStaff.query.filter(CourseStaff.year_id == year_db.id,CourseStaff.course_id == course.id, CourseStaff.staff_id==s.id).first()
        course_staff.workload=workload
        course_staff.nt_hours = nt_hours
        #REMOVE COORD ATTR FROM ALL OTHERS...
        if coord:
            course_staff_set = CourseStaff.query.filter(CourseStaff.year_id == year_db.id, CourseStaff.course_id == course.id).all()
            for cs in course_staff_set:
                cs.is_coordinator=0
                db.session.add(cs)

        course_staff.is_coordinator = coord
        db.session.add(course_staff)
        db.session.commit()

        return staff_home(VIEW_STAFF=-1,YEAR=year_db.number, VIEW_COURSE=c_name)#return jsonify({'status': 'OK', 'course_name': course.code, "title": course.title, 'student_factor': course.student_factor, 'students': course.expected_students, 'lecturers': staff_list, 'tri':course.trimester, 'coord': coord});



@main_views.route('/admin_edit_course_details', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_edit_course_details():

    year = request.form['year']
    c_name = request.form["course_name"]
    if "notes" in request.form:
        notes = request.form["notes"]
    expected_students = request.form["expected_students"]
    student_factor = request.form["student_factor"]
    current_app.logger.error("Editing entry...");

    if year:
        year_db = Years.query.filter(Years.number == year).first()
        course = Course.query.filter(Course.year_id == year_db.id, Course.code==c_name).first()
        if notes:
            course.notes=notes
        if expected_students:
                course.expected_students = expected_students
        if student_factor:
                course.student_factor = student_factor

        #REMOVE COORD ATTR FROM ALL OTHERS...
        db.session.add(course)
        db.session.commit()

        return staff_home(VIEW_STAFF=-1,YEAR=year_db.number, VIEW_COURSE=c_name)#return jsonify({'status': 'OK', 'course_name': course.code, "title": course.title, 'student_factor': course.student_factor, 'students': course.expected_students, 'lecturers': staff_list, 'tri':course.trimester, 'coord': coord});


@main_views.route('/admin_del_course', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_del_course():

    year = request.form['year']
    c_name = request.form["course_name"]
    s_name = request.form["staff_name"].strip("'")

    if year:
        year_db = Years.query.filter(Years.number == year).first()
        course = Course.query.filter(Course.year_id == year_db.id, Course.code == str(c_name)).first()
        s = Staff.query.filter(Staff.year_id == year_db.id, Staff.name == s_name).first()

        course_staff = CourseStaff.query.filter(CourseStaff.year_id == year_db.id,
                                                CourseStaff.course_id == course.id, CourseStaff.staff_id==s.id).first()
        if course_staff:
            db.session.delete(course_staff)
            db.session.commit()

        return staff_home(VIEW_STAFF=-1,YEAR=year_db.number, VIEW_COURSE=c_name)#return jsonify({'status': 'OK', 'course_name': course.code, "title": course.title, 'student_factor': course.student_factor, 'students': course.expected_students, 'lecturers': staff_list, 'tri':course.trimester, 'coord': coord});


def validate_model(mod):
    staff_list = []
    staff_load = []
    C_Lev =1
    S_Lab_Hours=1
    C_Lab_Hours =1
    COURSE_HOURS_PER_COURSE=1
    Course_Hours=1
    C_Stud_Fact =1
    C_Exp_Stud =1
    C_Status=1
    S_Buy = 1
    S_FTE = 1
    S_New = 1
    S_Admin=1
    S_Research = 1
    
    try:
        result=eval(mod)
        return 1
    except:
        return -1

@main_views.route('/admin_change_model', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_change_model():
    year = request.form['year']

    if "model_name" in request.form:
        model_name = request.form["model_name"]
        if model_name=="":
           model_name='default'
    else:       
           model_name='default'
    model_set_name = request.form["model_set_name"]
    operation = request.form["drop_down"]

    if "model" in request.form:
       model = str(request.form["model"])
    else:
       model=str("C_Status*Course_Hours + C_Stud_Fact*C_Exp_Stud")

    specificity=-1
    applicability=GENERAL_SELECTION
    if "Applicability" in request.form:
       applicability = str(request.form["Applicability"])
    if "applicability_dd" in request.form:
       applicability_dd = str(request.form["applicability_dd"])
    if "low_bound" in request.form: 
       low_thresh = int(request.form["low_bound"])
    if "hi_bound" in request.form:
       hi_thresh = int(request.form["hi_bound"])

    year_db=Years.query.filter(Years.number == year).first()
    if operation and (operation=="Add_Model_Set" or operation=="Add_Model" or operation=="Edit_Model"):
         if validate_model(model)==1:
            STUB=1; 
         else:
            return staff_home(VIEW_STAFF=-1, YEAR=year_db.number,VIEW_COURSE=-1, error_msg="MODEL WAS NOT PARSEABLE")
        
    if operation and operation=="Add_Model_Set":
        mse=Model_Set_Entity.query.filter(Model_Set_Entity.name==model_set_name).all()
        if mse:
           return staff_home(VIEW_STAFF=-1, YEAR=year_db.number, VIEW_COURSE=-1, error_msg="MODEL SET ALREADY EXISTS IN DATABASE" )
        else:
           #Test the specified model
               m=Model( model, year_db.id, model_name)
               db.session.add(m)
               db.session.commit()
               mse=Model_Set_Entity( specificity, m.id, GENERAL_SELECTION,model_set_name ,low_thresh*STORAGE_FRACTION , hi_thresh*STORAGE_FRACTION )
               db.session.add(mse)
               db.session.commit()
        
    if operation and operation=="Del_Model_Set":
        mse=Model_Set_Entity.query.filter(Model_Set_Entity.name==model_set_name).all()
        if mse:
          for m in mse:
               mod=Model.query.filter( m.model_id == Model.id).first()
               if mod:
                   db.session.delete(mod)
               db.session.delete(m)
          db.session.commit()     
           
        else:
           return staff_home(VIEW_STAFF=-1, YEAR=year_db.number,VIEW_COURSE=-1, error_msg="MODEL WAS NOT PRESENT")

    if operation and operation=="Add_Model":
         mse=Model_Set_Entity.query.filter(Model_Set_Entity.name==model_set_name).first()
         if mse:
           model2=Model.query.filter(Model.name==model_name).first()

           if model2:
                return staff_home(VIEW_STAFF=-1, YEAR=year_db.number, VIEW_COURSE=-1, error_msg="MODEL ALREADY EXISTS" )         

           if applicability=="Course_Model":
                  applicability=COURSE_SELECTION
                  course=Course.query.filter(Course.code==applicability_dd).first()
                  specificity=course.id
           elif applicability=="Discipline_Model":
                  applicability=DISCIPLINE_SELECTION
                  dis=Discipline.query.filter(Discipline.name==applicability_dd).first()
                  specificity=dis.id;                 
           elif applicability=="Level_Model":
                  applicability=LEVEL_SELECTION
                  specificity=applicability_dd
           elif applicability=="Discipline-Level_Model":
                  applicability=DISC_LEVEL_SELECTION  
                  dis=Discipline.query.filter(Discipline.name==applicability_dd[0:3]).first()
                  specificity= dis.id + applicability_dd[7]   #DISC_ID + Level (1,2,3...)
           else:
                  applicability=GENERAL_SELECTION
                  specificity=-1
           
           model=Model( model, year_db.id, model_name)
           db.session.add(model)
           db.session.commit()
           model=Model.query.filter(Model.name==model_name).first()          
           mse=Model_Set_Entity(specificity, model.id, applicability , model_set_name, mse.low_thresh*STORAGE_FRACTION, mse.hi_thresh*STORAGE_FRACTION)
           db.session.add(mse)
           db.session.commit()     
         else:
           return staff_home(VIEW_STAFF=-1, YEAR=year_db.number,VIEW_COURSE=-1, error_msg="MODEL SET ENTITY NOT FOUND" )         
         return staff_home(VIEW_STAFF=-1, YEAR=year_db.number,VIEW_COURSE=-1 )   
         
    if operation and operation=="Edit_Model":
         mse=Model_Set_Entity.query.filter(Model_Set_Entity.name==model_set_name).all()
         model=Model( model, year_db.id, model_name)
         if model:
           model=Model( model, year_db.id, model_name)
           db.session.add(model);
           db.session.commit() 
         else:
           return staff_home(VIEW_STAFF=-1, YEAR=year_db.number,VIEW_COURSE=-1, error_msg="MODEL WAS NOT PRESENT")
           
    if operation and operation=="Del_Model":
         if model_name!="default":
             mse=Model_Set_Entity.query.filter(Model_Set_Entity.name==model_set_name).all()
             if mse:
                for mse_i in mse:        
                   mod=Model.query.filter( mse_i.model_id == Model.id, model_name==Model.name).first()
                   if mod:
                         db.session.delete(mod)
                         db.session.commit()                    
                         db.session.delete(mse_i)
                         db.session.commit() 
             else:
                return staff_home(VIEW_STAFF=-1, YEAR=year_db.number, VIEW_COURSE=-1, error_msg="MODEL WAS NOT PRESENT")
    
    return staff_home(VIEW_STAFF=-1, YEAR=year_db.number,VIEW_COURSE=-1)





@main_views.route('/admin_view_log', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_view_log():
    year=request.values.get('year')    
    entry= request.values.get("log_entry")
    spec=request.values.get("spec")
    low_bound = datetime.strptime( request.values.get("low_bound"),'%d/%m/%Y')
    hi_bound = datetime.strptime(request.values.get("hi_bound"),'%d/%m/%Y')
    max_entries=int(request.values.get("max_entries"))
    today = datetime.now()
    current_app.logger.error("PARSED TIME:   " + low_bound.strftime('%d/%m/%Y'))
    if(max_entries < 1 ) :
       max_entries=100
    
    if(low_bound > today or low_bound > hi_bound) :  
       low_bound = today
          
    if(hi_bound > today or hi_bound < low_bound) :  
       hi_bound = today   
    
    log_norm=[]    
    log=[]
    if entry=='Course':
       spec_split=re.split("\s", spec,1)
       spec=spec_split[0]
       log=CourseLog.query.filter(Years.number == year, CourseLog.updated_at.between(low_bound, hi_bound), CourseLog.code==spec).limit(max_entries).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) )      

       log_hdr=[ 'code', 'title','trimester', 'expected_students' ,'is_offered', 'created_at','updated_at', 'status', 'student_factor', 'year_id','num_lectures_week', 'lecture_duration' ,'total_lab_hours', 'modified_by' ]
       log_norm=[ [x.code, x.title,x.trimester, x.expected_students ,x.is_offered, x.created_at,x.updated_at, x.status, x.student_factor, x.year_id,x.num_lectures_week, x.lecture_duration ,x.total_lab_hours, x.modified_by ] for x in log   ] 
    
    elif entry=='Association':
       cs=re.search('Course:([0-9A-Za-z\w]+)', spec);
       if cs is not None:
          x=cs.group(0);
          y=Course.query.filter(Years.number==year, Course.code==spec).first() 
          log=CourseStaffLog.query.filter(Years.number==year, CourseStaffLog.updated_at.between(low_bound, hi_bound), CourseStaffLog.course_id==y.code).limit(max_entries).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) )    
       else:          
          cs=re.search('Staff:([0-9A-Z\+a-z\w]+)', spec);
          x=cs.group(0);
          x.replace('+',' ');
          y=Staff.query.filter(Years.number==year, Staff.name==x).first() 
          if y is not None:
           log=CourseStaffLog.query.filter(Years.number==year, CourseStaffLog.updated_at.between(low_bound, hi_bound), CourseStaffLog.staff_id==y.id).limit(max_entries).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) )    
           log_hdr=['course_id', 'staff_id','workload', 'is_coordinator' , 'updated_at','created_at','year_id', 'nt_hours', 'modified_by' ] 
       if log:   
          log_norm=[ [x.course_id, x.staff_id, x.workload, x.is_coordinator , x.updated_at, x.created_at, x.year_id, x.nt_hours, x.modified_by ] for x in log   ] 
 
    elif entry=='Staff':
        log=StaffLog.query.filter(Years.number == year, StaffLog.updated_at.between(low_bound, hi_bound), StaffLog.name==spec.replace('+',' ')).limit(max_entries).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) ) 
        log_hdr=['name', 'admin_workload','research_workload', 'full_time_equivalent' ,'is_new', 'notes', 'created_at', 'updated_at','buyout', 'leave','discipline_id', 'year_id' ,'image_url', 'modified_by' ] 
        if log:   
           log_norm=[ [x.name, x.admin_workload,x.research_workload, x.full_time_equivalent ,x.is_new, x.notes, x.created_at, x.updated_at,x.buyout, x.leave,x.discipline_id, x.year_id ,x.image_url, x.modified_by ] for x in log   ] 
     
    elif entry=='Model':
        log=ModelLog.query.filter(Years.number == year, ModelLog.updated_at.between(low_bound, hi_bound)).limit(max_entries).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) ) 
        log_hdr=['equation', 'name', 'created_at', 'updated_at', 'year_id',  'modified_by' ]
        if log:   
           log_norm=[ [x.equation, x.name, x.created_at, x.updated_at, x.year_id,  x.modified_by ] for x in log   ] 
     
    return jsonify({'status': 'OK', 'set': log_norm, 'set_hdr': log_hdr});



@main_views.route('/admin_get_list', methods=['GET', 'POST'])
#@group_required('ecs')
@appauth_required('workload-admin')
def admin_get_list():
    #current_app.logger.debug("This is the model:  safdsafdsfdsafd " )
    year=request.values.get('year')
    
    #current_app.logger.debug("This is the yerar:   " +year)
    specification= request.values.get("log_entry")
    yid=Years.query.filter(Years.number==year).first().id ;
    spec_list=yid;
    if specification=='Course':
       spec=Course.query.filter(Course.year_id==yid).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) )      
       spec_list=[ [x.code +" : "+ x.title+ " : " +x.trimester] for x in spec ] 
    
    elif specification=='Association':
       spec2=Course.query.filter(Course.year_id==yid).all()
       spec=Staff.query.filter(Staff.year_id==yid).all()
       s_list=[ ['Staff:' + x.name ] for x in spec  ]
       s_list2=[ ['Course:' + x.code ] for x in spec2  ]
       spec_list=s_list+s_list2;       
                  
    elif specification=='Staff':
        spec=Staff.query.filter(yid==Staff.year_id).all() #<= '1988-01-17', User.birthday >= '1985-01-17')) ) 
        spec_list=[ [x.name] for x in spec   ] 
 
    return jsonify({'status': 'OK', 'set': spec_list});



@main_views.route('/admin_get_model', methods=['GET', 'POST'])
#@group_required('ecs')
@group_required('ecs')
def admin_get_model( Model_set_name="default", year=-1):
    year=request.args.get('year')
    staff_dict={}
    debug='';
    
    Model_set_name= request.values.get("Model_set_name")
    year= request.values.get("year")
    if not year:
        year = date.today().year

    year_db = Years.query.filter(Years.number == year).first()
    staff_set = Staff.query.filter(Staff.year_id == year_db.id).all()

    for sm in staff_set:
        staff_dict[sm.name]=sm

    discipline_set = Discipline.query.filter().all()     

    #STAFF MODEL BASED
    model_group_workload_sum = {}  # group_set [disc][staff][trimester] workload

    mod = Model_Set_Entity.query.filter(Model_Set_Entity.name == Model_set_name).first();
     
    for disc in discipline_set:
        staff_set2=Staff.query.filter(Staff.discipline_id == disc.id, Staff.year_id==year_db.id).all()
        model_group_workload_sum[str(disc.name)] = {}
                    
        # BEGIN COURSES DS.
        for s in staff_set2:
            cs_set=CourseStaff.query.filter(CourseStaff.staff_id==s.id,CourseStaff.year_id==year_db.id).all()

            #model based...
            model_group_workload_sum[str(disc.name)][str(s.name)] = {}
            model_group_workload_sum[str(disc.name)][str(s.name)]['1'] = 0
            model_group_workload_sum[str(disc.name)][str(s.name)]['2'] = 0
            model_group_workload_sum[str(disc.name)][str(s.name)]['3'] = 0
            model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = 0;
            model_group_workload_sum[str(disc.name)][str(s.name)]['Total_General'] = s.research_workload + s.admin_workload;
            model_group_workload_sum[str(disc.name)][str(s.name)]['Research'] = s.research_workload;
            model_group_workload_sum[str(disc.name)][str(s.name)]['Admin'] = s.admin_workload;
                
            for cs in cs_set:
                c = Course.query.filter(Course.id == cs.course_id).first()
                                
                if c.trimester=='F':
                    #MODEL BASED
                    model_group_workload_sum[str(disc.name)][str(s.name)]['1'] = model_group_workload_sum[str(disc.name)][str(s.name)]['1'] + calc_workload(get_model(c,Model_set_name),cs.workload / 2, s, c, cs)  # int(cs.workload/2)  #calc_workload(get_model(c,Model,cs.workload/2, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent);    #//int(cs.workload/2)       #(workload,students=0,new_staff=0,stud_fact=0,level=0, num_courses=0,buyout=0, fte=0): //calculate_workload #//
                    model_group_workload_sum[str(disc.name)][str(s.name)]['2'] = model_group_workload_sum[str(disc.name)][str(s.name)]['2'] + calc_workload(get_model(c,Model_set_name),cs.workload / 2, s, c, cs)  # int(cs.workload/2) # calc_workload(get_model(c,Model,cs.workload/2, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//       #//
                    model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] + calc_workload(get_model(c,Model_set_name),cs.workload , s, c, cs)  # cs.workload #calc_workload(get_model(c,Model,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//     #//
                  
                else:
                    model_group_workload_sum[str(disc.name)][str(s.name)][str(c.trimester)] = model_group_workload_sum[str(disc.name)][str(s.name)][str(c.trimester)] + calc_workload(get_model(c,Model_set_name),cs.workload , s, c,cs) #   model_group_workload_sum[str(disc.name)][str(s.name)]['Total'] = \
                    model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] = model_group_workload_sum[str(disc.name)][str(s.name)]['Total_Courses'] + calc_workload(get_model(c,Model_set_name),cs.workload , s, c, cs)  # cs.workload #calc_workload(mod,cs.workload, c.expected_students, s.is_new, c.student_factor, int(c.code[4]+'0'+'0'), 0, s.buyout, s.full_time_equivalent); #//     #//


    return jsonify({'status': 'OK', 'COURSE_HOURS_PER_COURSE':COURSE_HOURS_PER_COURSE,'HI_THRESH':mod.hi_thresh/STORAGE_FRACTION, 'MED_THRESH':mod.low_thresh/STORAGE_FRACTION, 'debug':debug, 'model':Model_set_name, 'model_group_workload':model_group_workload_sum})  # PASS the form to the template renderer...


#FUTURE RELEASES "MAY" INCLUDE THESE NEXT FEW FEATURES...
@main_views.route('/admin_staff_panic', methods=['GET', 'POST'])
#@group_required('ecs')
@group_required('ecs')
def admin_staff_panic( staff_name, year=-1):
    year=request.args.get('year')
    staff_dict={}
    debug='';
    
    Model_set_name= request.values.get("Model_set_name")
    year= request.values.get("year")
    if not year:
        year = date.today().year

    year_db = Years.query.filter(Years.number == year).first()
    staff_set = Staff.query.filter(Staff.year_id == year_db.id).all()

    return jsonify({'status': 'OK', 'COURSE_HOURS_PER_COURSE':COURSE_HOURS_PER_COURSE,'HI_THRESH':1500, 'MED_THRESH':500, 'debug':debug, 'model':Model_set_name, 'model_group_workload':model_group_workload_sum})  # PASS the form to the template renderer...



@main_views.route('/admin_staff_feedback', methods=['GET', 'POST'])
#@group_required('ecs')
@group_required('ecs')
def admin_staff_feedback( staff_name, year=-1):
    year=request.args.get('year')
    staff_dict={}
    debug='';
    
    Model_set_name= request.values.get("Model_set_name")
    year= request.values.get("year")
    if not year:
        year = date.today().year

    year_db = Years.query.filter(Years.number == year).first()
    staff_set = Staff.query.filter(Staff.year_id == year_db.id).all()

    return jsonify({'status': 'OK', 'COURSE_HOURS_PER_COURSE':COURSE_HOURS_PER_COURSE,'HI_THRESH':1500, 'MED_THRESH':500, 'debug':debug, 'model':Model_set_name, 'model_group_workload':model_group_workload_sum})  # PASS the form to the template renderer...

