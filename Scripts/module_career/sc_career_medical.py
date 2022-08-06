import random

import date_and_time
import services
from module_career.sc_career_functions import get_routine_sims
from module_career.sc_career_routines import sc_CareerRoutine
from scripts_core.sc_autonomy import set_autonomy
from scripts_core.sc_jobs import check_actions, clear_sim_instance, action_timeout, get_action_timestamp, \
    find_all_objects_by_title, push_sim_function, debugger, get_career_level, get_skill_level, remove_sim_buff, \
    distance_to_by_room, assign_title, assign_routine, set_exam_info
from scripts_core.sc_script_vars import sc_Vars
from scripts_core.sc_util import init_sim
from sims.sim_info import SimInfo
from sims.sim_info_types import Age


class sc_CareerMedicalExams:
    def __init__(self, doctor=None, patient=None, exam=None, time=None, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.doctor = doctor
        self.patient = patient
        self.exam = exam
        self.time = time


setattr(SimInfo, "exam_info", sc_CareerMedicalExams())

class sc_CareerMedical(sc_CareerRoutine):
    def __init__(self):
        super().__init__()
        self.doctor_exams = [110842, 116412, 111623, 105942, 179422]
        
    def set_patient(self, doctor):
        patient_sims = [sim for sim in services.sim_info_manager().instanced_sims_gen()
            if [role for role in sim.autonomy_component.active_roles() if "patient" in str(role).lower()]]

        if not patient_sims:
            return
        for exam in sc_Vars.exam_list:
            if [sim for sim in patient_sims if sim == exam.patient and sim.sim_info.routine_info.title != "patient"]:
                sc_Vars.exam_list.remove(exam)

        for sim in list(patient_sims):
            if not [exam for exam in sc_Vars.exam_list if exam.doctor == doctor or exam.patient == sim] \
                    or not len(sc_Vars.exam_list):
                now = services.time_service().sim_now
                sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, None, now))
                set_exam_info(sim.sim_info)
                assign_routine(sim.sim_info, "patient", False)

                    
    def get_patient(self, doctor):
        if not [sim for sim in services.sim_info_manager().instanced_sims_gen()
                if [exam for exam in sc_Vars.exam_list if exam.patient == sim]]:
            sc_Vars.exam_list = []
            return

        for exam in sc_Vars.exam_list:
            if exam.doctor == doctor:
                set_exam_info(exam.patient.sim_info)
                return exam.patient

    def get_exam_time(self, patient):
        for exam in sc_Vars.exam_list:
            if exam.patient == patient:
                return exam.time

    def get_patient_exam(self, patient):
        for exam in sc_Vars.exam_list:
            if exam.patient == patient:
                set_exam_info(patient.sim_info)
                return exam.exam

    def set_patient_exam(self, patient, exam_id):
        doctor = None
        for exam in sc_Vars.exam_list:
            if exam.patient == patient:
                doctor = exam.doctor
                exam.exam = exam_id
                exam.time = services.time_service().sim_now
                set_exam_info(patient.sim_info)

        if exam_id == 105841:
            if sc_Vars.DEBUG:
                debugger("X-Ray machines being calibrated.")
        elif exam_id == 105942:
            if sc_Vars.DEBUG:
                debugger("X-Ray exam scheduled.")
        elif exam_id == 111129 or exam_id == 111130:
            if sc_Vars.DEBUG:
                debugger("Treatment scheduled.")
        elif exam_id == 111623:
            if sc_Vars.DEBUG:
                debugger("Treadmill exam scheduled.")
        elif exam_id:
            if sc_Vars.DEBUG:
                debugger("Exam {} scheduled.".format(exam_id))
        else:
            if sc_Vars.DEBUG:
                debugger("Exam being carried out.")

    def treat_patient(self, doctor):
        sim = None
        for exam in sc_Vars.exam_list:
            if exam.doctor == doctor:
                sim = exam.patient
                sc_Vars.exam_list.remove(exam)
        if sim:
            assign_title(sim.sim_info, "Treated")
            now = services.time_service().sim_now
            sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, -1, now))
            set_exam_info(sim.sim_info)

    def transfer_patient(self, doctor, exam_id, target, patient=None):
        if patient is None:
            for exam in sc_Vars.exam_list:
                if exam.doctor == doctor:
                    patient = exam.patient
                    sc_Vars.exam_list.remove(exam)
        else:
            for exam in sc_Vars.exam_list:
                if exam.patient == patient:
                    sc_Vars.exam_list.remove(exam)

        if patient is None:
            return
        clear_sim_instance(patient.sim_info)
        routine_sims = get_routine_sims()
        if [sim for sim in routine_sims if sim == patient and sim.sim_info.routine_info.title == "diagnosed"]:
            self.diagnose_patient(doctor)
        if isinstance(target, str):
            # Transfer to radiologist
            for sim in routine_sims:
                if sim.sim_info.routine_info.title == target:
                    now = services.time_service().sim_now
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(sim, patient, exam_id, now))
                    set_exam_info(patient.sim_info)
                    if sc_Vars.DEBUG:
                        debugger("Exam {} scheduled for patient. Patient transferred to {}".format(str(exam_id),
                                                                                              target.title()))
                    return
            if sc_Vars.DEBUG:
                debugger("Exam {} scheduled for patient. Patient cannot be transferred to {}. No {} on duty!".format(
                    str(exam_id), target.title(), target.title()))
            now = services.time_service().sim_now
            sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, patient, None, now))
            set_exam_info(patient.sim_info)
        else:
            # Transfer back to doctor
            for sim in routine_sims:
                if sim == target:
                    now = services.time_service().sim_now
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(sim, patient, exam_id, now))
                    set_exam_info(patient.sim_info)
                    if sc_Vars.DEBUG:
                        debugger("Exam {} scheduled for patient. Patient transferred to {} {}".format(str(exam_id),
                                                                                                      target.first_name,
                                                                                                      target.last_name))
                    return
                
    def discharge_patient(self, doctor):
        sim = None
        for exam in sc_Vars.exam_list:
            if exam.doctor == doctor:
                sim = exam.patient
                sc_Vars.exam_list.remove(exam)
                set_exam_info(sim.sim_info)
        if sim:
            assign_routine(sim.sim_info, "leave")

    def diagnose_patient(self, doctor):
        sim = None
        for exam in sc_Vars.exam_list:
            if exam.doctor == doctor:
                sim = exam.patient
                sc_Vars.exam_list.remove(exam)
        if sim:
            assign_routine(sim.sim_info, "disgnosed")
            now = services.time_service().sim_now
            buff_component = sim.sim_info.Buffs
            sickness = ""
            if buff_component is not None:
                for buff in buff_component:
                    buff_title = buff.__class__.__name__
                    if "diagnosed_" in buff_title.lower() or "illness" in buff_title.lower() or "sickness" in buff_title.lower():
                        sickness = sickness + "," + buff_title.lower()
            if sickness != "":
                if "bloatyhead" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Bloaty Head. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111129, now))
                    set_exam_info(sim.sim_info)
                elif "burningtummy" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Burning Tummy. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111129, now))
                    set_exam_info(sim.sim_info)
                elif "gasandgiggles" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Gas & Giggles. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111130, now))
                    set_exam_info(sim.sim_info)
                elif "itchy" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Itchy Plumbob. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111129, now))
                    set_exam_info(sim.sim_info)
                elif "llamaflu" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Llama Flu. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111129, now))
                    set_exam_info(sim.sim_info)
                elif "starry" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Starry Eyes. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111130, now))
                    set_exam_info(sim.sim_info)
                elif "sweaty" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Sweaty Shivers. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111129, now))
                    set_exam_info(sim.sim_info)
                elif "triple" in sickness:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, Triple Threat. Patient waiting for cure.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, 111129, now))
                    set_exam_info(sim.sim_info)
                else:
                    if sc_Vars.DEBUG:
                        debugger("Diagnosis, No Symptoms. Patient discharged.")
                    sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, None, now))
                    set_exam_info(sim.sim_info)
                    self.discharge_patient(doctor)
                    return
            else:
                if sc_Vars.DEBUG:
                    debugger("Diagnosis, No diagnosis available. Patient discharged.")
                sc_Vars.exam_list.append(sc_CareerMedicalExams(doctor, sim, None, now))
                set_exam_info(sim.sim_info)
                self.discharge_patient(doctor)
                
    def diagnosis_skill(self, doctor):
        # success based on logic and mood
        logic_skill = get_skill_level(16706, doctor)
        sim_level = get_career_level(doctor.sim_info)
        mood = doctor.sim_info.get_mood()
        mood_intensity = doctor.sim_info.get_mood_intensity()
        if mood is not None:
            sim_mood = mood.guid64
        else:
            sim_mood = 0
        mood_multiplier = 0
        if sim_mood == 14632 or sim_mood == 14645 or sim_mood == 14646:
            mood_multiplier = -5 * (mood_intensity + 1)
        elif sim_mood == 14639:
            mood_multiplier = 5 * (mood_intensity + 1)
        elif sim_mood != 14639:
            remove_sim_buff(112667, doctor.sim_info)
            remove_sim_buff(112668, doctor.sim_info)
            if sc_Vars.DEBUG:
                debugger("Removed research buffs.")

        return ((float(logic_skill) * 10.0) * 0.5) + (
                float(sim_level) * 2.0) + mood_multiplier
    
    def doctor_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            if sim_info.routine_info.title == "on break":
                return
            if check_actions(sim, "gohere"):  # staff_room
                clear_sim_instance(sim.sim_info, "gohere", True)
                return
            if check_actions(sim, "research"):
                return
            patient = self.get_patient(sim)
            exam = 110842
            if patient:
                set_autonomy(sim_info, 4)
                if check_actions(sim, "examine_thorough"):
                    if action_timeout(sim, "examine_thorough", 1):
                        clear_sim_instance(sim.sim_info)
                    if sc_Vars.DEBUG:
                        debug_text = "Thorough Examine Timestamp: {} - On Patient: {} {}".format(
                            get_action_timestamp(sim, "examine_thorough"), patient.first_name,
                            patient.last_name)
                        debugger(debug_text)
                    return
                if check_actions(sim, "research"):
                    return
                if check_actions(sim, "treadmill") and check_actions(patient, "treadmill"):
                    now = services.time_service().sim_now
                    if now - self.get_exam_time(patient) > date_and_time.create_time_span(minutes=10):
                        clear_sim_instance(patient.sim_info)
                        clear_sim_instance(sim.sim_info)
                    return

                chance = random.uniform(0, 100)
                skill = self.diagnosis_skill(sim)

                if distance_to_by_room(sim, patient) > 1:
                    exam = self.doctor_exams[0]
                elif self.get_patient_exam(patient):
                    exam = self.get_patient_exam(patient)
                    self.set_patient_exam(patient, 0)
                else:
                    if chance < skill:
                        exam = self.doctor_exams[len(self.doctor_exams) - 1]
                    else:
                        exam = self.doctor_exams[random.randint(1, len(self.doctor_exams) - 2)]

                if sc_Vars.DEBUG:
                    debug_text = "Diagnosis Skill: {:.2f}% > chance {:.2f}% - Exam {} on Patient: {} {}".format(skill,
                                                                                                    chance,
                                                                                                    exam,
                                                                                                    patient.first_name,
                                                                                                    patient.last_name)
                    debugger(debug_text)

                if exam == 111129 or exam == 111130:
                    clear_sim_instance(sim.sim_info)
                    push_sim_function(sim, patient, exam)
                    self.treat_patient(sim)
                elif exam == -1:
                    clear_sim_instance(sim.sim_info)
                    if sc_Vars.DEBUG:
                        debugger("Patient is ready to be discharged!")
                    self.discharge_patient(sim)
                elif exam == 179422:
                    clear_sim_instance(sim.sim_info)
                    push_sim_function(sim, patient, exam)
                    if sc_Vars.DEBUG:
                        debugger("Patient is ready to be cured!")
                    self.diagnose_patient(sim)
                elif exam == 111623:
                    clear_sim_instance(sim.sim_info)
                    treadmills = find_all_objects_by_title(sim, "treadmill")
                    if not treadmills:
                        self.transfer_patient(sim, 105942, "radiologist")
                        return
                    if patient.age < Age.YOUNGADULT:
                        exam = self.doctor_exams[0]
                    push_sim_function(sim, patient, exam)
                    if patient.age > Age.TEEN:
                        clear_sim_instance(patient.sim_info)
                        push_sim_function(patient, sim, 111624)
                elif exam == 105942:
                    clear_sim_instance(sim.sim_info)
                    self.transfer_patient(sim, 105942, "radiologist")
                else:
                    clear_sim_instance(sim.sim_info)
                    push_sim_function(sim, patient, exam)

            
    def medical_staff_routine(self, sim_info):
        sim = init_sim(sim_info)
        if sim:
            if sim_info.routine_info.title == "on break":
                return True
            if check_actions(sim, "gohere"):  # staff_room
                clear_sim_instance(sim.sim_info, "gohere", True)
                return True
            if check_actions(sim, "research"):
                return True
            if check_actions(sim, "consume"):
                return True
    
            patient = self.get_patient(sim)
            if patient:
                if sim_info.routine_info.title == "doctor":
                    self.doctor_routine(sim_info)
                    return True
                if sim_info.routine_info.title == "radiologist":
                    #self.radiologist_routine(sim_info)
                    self.transfer_patient(sim, 110842, "doctor")
                    return True
            else:
                if sim_info.routine_info.title == "radiologist":
                    self.staff_routine(sim_info)
                    return True
                elif sim_info.routine_info.title == "doctor":
                    self.set_patient(sim)
                    choice = random.randint(1, 3)
                elif sim_info.routine_info.title == "pathologist":
                    choice = random.randint(1, 5)
                elif sim_info.routine_info.title == "intern":
                    choice = random.randint(1, 1)
                else:
                    choice = random.randint(1, 3)
    
                chance = random.uniform(0.0, 100.0)
                if check_actions(sim, "_sit") and not check_actions(sim, "browse_web") or \
                        check_actions(sim, "sit_") and not check_actions(sim, "browse_web"):
                    choice = 1
                elif check_actions(sim, "browse_web"):
                    if chance < 90.0:
                        choice = 1
                elif check_actions(sim, "analyze"):
                    if chance < 90.0:
                        choice = 2
                elif check_actions(sim, "chemistry"):
                    if chance < 90.0:
                        choice = 3
                elif check_actions(sim, "chamber-examine-female"):
                    if action_timeout(sim, "chamber-examine-female", 1.5):
                        clear_sim_instance(sim.sim_info)
                    else:
                        choice = 4
                elif check_actions(sim, "chamber-examine-organ"):
                    if action_timeout(sim, "chamber-examine-organ", 1):
                        clear_sim_instance(sim.sim_info)
                    else:
                        choice = 5

                if sc_Vars.DEBUG:
                    debug_text = ""
                    doing = "Nothing"
                    if choice == 1:
                        doing = "Browse Web"
                    elif choice == 2:
                        doing = "Practice Analysis"
                    elif choice == 3:
                        doing = "Experiment"
                    elif choice == 4:
                        doing = "Place toetag"
                    elif choice == 5:
                        doing = "Weigh organs"
                    debug_text = debug_text + "Routine {} {} - Chance: {:.2f}% - Choice: {}".format(sim.first_name, sim.last_name, chance, doing)
                    debugger("{}".format(debug_text))

                use_object1 = None
                use_object2 = None
                if choice == 1:
                    if not check_actions(sim, "browse_web") and not check_actions(sim, "_sit") and \
                            not check_actions(sim, "sit_"):
                        use_objects = find_all_objects_by_title(sim, "computer")
                        if use_objects:
                            use_object1 = next(iter(use_objects))
                            use_objects = find_all_objects_by_title(use_object1,
                                                                        "sitliving|sitdining|sitsofa|chair|stool",
                                                                        use_object1.level, 1)
                        if use_objects and use_object1:
                            use_object2 = next(iter(use_objects))
                            clear_sim_instance(sim.sim_info, "chat|browse|_sit|sit_", True)
                            if "stool" in str(use_object2).lower():
                                push_sim_function(sim, use_object2, 157667)
                            else:
                                push_sim_function(sim, use_object2, 31564)
                        if use_object1 is not None:
                            push_sim_function(sim, use_object1, 13187)
                    elif check_actions(sim, "_sit") and not check_actions(sim, "browse_web") or \
                            check_actions(sim, "sit_") and not check_actions(sim, "browse_web"):
                        use_objects = find_all_objects_by_title(sim, "computer")
                        if use_objects:
                            use_object1 = next(iter(use_objects))
                            clear_sim_instance(sim.sim_info, "chat|browse|_sit|sit_", True)
                            push_sim_function(sim, use_object1, 13187)
                elif choice == 2:
                    if not check_actions(sim, "analyzer"):
                        use_objects = find_all_objects_by_title(sim, "analyzer")
                        if use_objects:
                            use_object1 = next(iter(use_objects))
                            clear_sim_instance(sim.sim_info, "chat|analyzer", True)
                            push_sim_function(sim, use_object1, 104725)
                elif choice == 3:
                    if not check_actions(sim, "chemistry"):
                        use_objects = find_all_objects_by_title(sim, "chemistry")
                        if use_objects:
                            use_object1 = next(iter(use_objects))
                            clear_sim_instance(sim.sim_info, "chat|chemistry", True)
                            push_sim_function(sim, use_object1, 105215)
                elif choice == 4:
                    if not check_actions(sim, "chamber-examine-female"):
                        coolers = [obj for obj in services.object_manager().get_all() if
                                   "morgue_chamber" in str(obj).lower()]
                        use_object1 = coolers[random.randint(0, len(coolers) - 1)]
                        if use_object1 is not None:
                            clear_sim_instance(sim.sim_info, "chat|chamber-examine-female", True)
                            push_sim_function(sim, use_object1, 13281576249128120844)
                elif choice == 5:
                    if not check_actions(sim, "chamber-examine-organ"):
                        use_objects = find_all_objects_by_title(sim, "morgue_scale")
                        if use_objects:
                            use_object1 = next(iter(use_objects))
                            clear_sim_instance(sim.sim_info, "chat|chamber-examine-organ", True)
                            push_sim_function(sim, use_object1, 18387193298570776595)
        return True
