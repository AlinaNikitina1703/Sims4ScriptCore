import services
from sims4.resources import Types


class sc_Affordance:

    def __init__(self, obj):
        super().__init__()
        self.affordance_object = obj
        self.affordances = obj._super_affordances
        self.affordance_instances = self.get_affordance_instances_from_object()
        self.affordance_names = self.get_affordance_names_from_object()

    def get_instance_from_manager(self, instance_manager, instance_id):
        return instance_manager.get(instance_id)

    def get_affordance_instances_from_object(self):
        return tuple(affordance for affordance in self.get_affordance_instances_gen())

    def get_affordance_names_from_object(self):
        return {affordance.guid64: self.get_affordance_name(affordance) for affordance in self.get_affordance_instances_gen()}

    def get_affordance_name(self, interaction):
        return str(interaction.affordance).replace("<class 'sims4.tuning.instances.", "").replace("'>", "")

    def get_affordance_instances_gen(self):
        affordance_manager = services.get_instance_manager(Types.INTERACTION)
        for affordance in self.affordances:
            affordance_instance = self.get_instance_from_manager(affordance_manager, affordance.guid64)
            if affordance_instance is not None:
                yield affordance_instance

    def get_affordance_instance(self, id):
        affordance_manager = services.get_instance_manager(Types.INTERACTION)
        affordance_instance = self.get_instance_from_manager(affordance_manager, id)
        if affordance_instance is not None:
            return affordance_instance

    def add_instances_to_object(self, instances):
        for instance in instances:
            if instance not in self.affordance_instances:
                self.affordance_instances += tuple([instance])

    def add_instance_id_to_object(self, id):
        instance = self.get_affordance_instance(id)
        if instance not in self.affordance_instances:
            self.affordance_instances += tuple([instance])
            return True
        return False

    def remove_instance_id_from_object(self, id):
        affordance_list = self.affordance_instances
        self.affordance_instances = ()
        for affordance in affordance_list:
            if id != affordance.guid64:
                self.affordance_instances += tuple([affordance])

    def retain_default_affordances(self):
        self.affordance_object._super_affordances = self.affordances

    def set_new_affordances(self):
        self.affordance_object._super_affordances = self.affordance_instances

