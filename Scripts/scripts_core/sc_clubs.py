from scripts_core.sc_jobs import clear_sim_instance, assign_title


class C_ZoneClubs:

    def __init__(self):
        super().__init__()

    def label_club_members(self, club):
        for sim_info in club.members:
            clear_sim_instance(sim_info, "sit", True)
            assign_title(sim_info, self.get_club_name(club))
        clear_sim_instance(club.leader, "sit", True)
        assign_title(club.leader, self.get_club_name(club))

    def clear_label_from_club_members(self, club):
        for sim_info in club.members:
            assign_title(sim_info, "")
        assign_title(club.leader, "")

    def get_club_name(self, club):
        if club is not None:
            if club._name is not None:
                return str(club._name).title()
            if club.club_seed is not None:
                return str(club.club_seed.name).title()
        return None

    def get_club_seed_name(self, seed):
        if seed:
            return str(seed).replace("<class 'sims4.tuning.instances.clubSeed_", "").replace('InitialSeeds_', '').replace("'>", "").title()
        else:
            return None

    def club_setup_on_load(self, club_service):
        for club in list(club_service.clubs):
            gathering = club_service.clubs_to_gatherings_map.get(club)
            if gathering:
                self.label_club_members(club)

sc_club = C_ZoneClubs()

def sc_club_gathering_start_handler(self, club, *args, **kwargs):
    global sc_club
    sc_club.label_club_members(club)

def sc_club_gathering_end_handler(self, club, *args, **kwargs):
    global sc_club
    sc_club.clear_label_from_club_members(club)
    return

def sc_club_on_zone_load_handler(self, *args, **kwargs):
    global sc_club
    sc_club.club_setup_on_load(self)
    return

