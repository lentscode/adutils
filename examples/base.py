from adutils import Exploit


class Trial(Exploit):
    def run(self, ip):
        print(ip)
        self.flagout(ip)

    def get_flag_ids(self):
        pass

    def submit_flags(self):
        pass


trial = Trial(1235, "TEAM_TOKEN", ignore=[0, 46])
trial.start()
