import sys
import optparse
import NiceNum
import Configuration
from MySQLUtils import MySQLUtils
from Reporter import Reporter
import TextUtils
import traceback


class User:
    def __init__(self, user_name):
        self.user = user_name
        self.success = [0, 0]
        self.failure = [0, 0]

    def add_success(self, njobs, wall_duration):
        """

        :param njobs:
        :param wall_duration:
        :return:
        """
        self.success = [int(njobs), float(wall_duration)]

    def add_failure(self, njobs, wall_duration):
        """

        :param njobs:
        :param wall_duration:
        :return:
        """
        self.failure = [int(njobs), float(wall_duration)]

    def get_failure_rate(self):
        """

        :return:
        """
        failure_rate = 0
        if self.success[0]+self.failure[0] > 0:
            failure_rate = self.failure[0]*100./(self.success[0]+self.failure[0])
        return failure_rate

    def get_waste_per(self):
        """

        :return:
        """
        waste_per = 0
        if self.success[1]+self.failure[1] > 0:
            waste_per = self.failure[1]*100./(self.success[1]+self.failure[1])
        return waste_per


class Experiment:
    """

    """
    def __init__(self, exp_name):
        """

        :param exp_name:
        :return:
        """
        self.experiment = exp_name
        self.success = [0, 0]
        self.failure = [0, 0]
        self.users = {}

    def add_user(self, user_name, user):
        self.users[user_name] = user

    def add_success(self, njobs, wall_duration):
        """

        :param njobs:
        :param wall_duration:
        :return:
        """
        self.success[0] += int(njobs)
        self.success[1] += float(wall_duration)

    def add_failure(self, njobs, wall_duration):
        """

        :param njobs:
        :param wall_duration:
        :return:
        """
        self.failure = [int(njobs), float(wall_duration)]

    def get_failure_rate(self):
        """

        :return:
        """
        failure_rate = 0
        if self.success[0]+self.failure[0] > 0:
            failure_rate = self.failure[0]*100./(self.success[0]+self.failure[0])
        return failure_rate

    def get_waste_per(self):
        """

        :return:
        """
        waste_per = 0
        if self.success[1]+self.failure[1] > 0:
            waste_per = self.failure[1]*100./(self.success[1]+self.failure[1])
        return waste_per


class WastedHoursReport(Reporter):
    """

    """
    def __init__(self, config_file, start, end, is_test=True, verbose=False):
        """
        :param config_file:
        :param start:
        :param end:
        :param is_test:
        :param verbose:
        :return:
        """
        Reporter.__init__(self, config_file, start, end, verbose)
        self.is_test = is_test
        self.experiments = {}
        self.connect_str = None

    def generate(self):
        """

        :return:
        """
        mysql_client_cfg = MySQLUtils.createClientConfig("main_db", self.config)
        self.connect_str = MySQLUtils.getDbConnection("main_db", mysql_client_cfg, self.config)
        select = "select VO.VOName,CommonName,if (ApplicationExitCode=0,'Success','Failure') as Status,sum(NJobs) as NJobs," + \
               "round(sum(WallDuration*Cores/3600.),1) as WallHours from MasterSummaryData m " + \
               "JOIN VONameCorrection VC ON (VC.corrid=m.VOcorrid) JOIN VO on (VC.void = VO.void) " + \
               "where EndTime>'"+self.start_time + "' AND EndTime < '"+self.end_time + \
               "' and probename like 'condor:fifebatch%.fnal.gov' group by status,VOName,CommonName order by VO.VOName,CommonName,status;"
        if self.verbose:
            print >> sys.stdout, select

        results, return_code = MySQLUtils.RunQuery(select, self.connect_str)
        if return_code != 0:
            raise Exception('Error to access mysql database')
        if self.verbose:
            print >> sys.stdout, results

        if len(results) == 1 and len(results[0].strip()) == 0:
            print >> sys.stdout, "Nothing to report"
            return

        for line in results:
            tmp = line.split('\t')
            name = tmp[0]
            uname = tmp[1]
            status = tmp[2]
            count = int(tmp[3])
            hours = float(tmp[4])
            if not self.experiments.has_key(name):
                exp = Experiment(name)
                self.experiments[name] = exp 
            else:
                exp = self.experiments[name]
            if not exp.users.has_key(uname):
                user = User(uname)
                exp.add_user(uname, user)
            if status == "Success":
                user.add_success(count, hours)
                exp.add_success(count, hours)
            else:
                user.add_failure(count, hours)
                exp.add_failure(count, hours)
        MySQLUtils.removeClientConfig(mysql_client_cfg)

    def send_report(self):
        if len(self.experiments) == 0:
            return
        table = ""
        for key, exp in self.experiments.items():
            for uname, user in exp.users.items():
                failure_rate = round(user.get_failure_rate(), 1)
                waste_per = round(user.get_waste_per(), 1)
                table += '\n<tr><td align="left">%s</td><td align="left">%s</td><td align="right">%s</td><td align="right">%s</td><td align="right">%s</td><td align="right">%s</td><td align="right">%s</td><td align="right">%s</td></tr>' %\
                      (key, uname, NiceNum.niceNum(user.success[0]+user.failure[0]),  NiceNum.niceNum(user.failure[0]), failure_rate, NiceNum.niceNum(user.success[1]+user.failure[1], 1), NiceNum.niceNum(user.failure[1], 1), waste_per)
        text = "".join(open("template_wasted_hours.html").readlines())
        text = text.replace("$START", self.start_time)
        text = text.replace("$END", self.end_time)
        text = text.replace("$TABLE", table)
        fn = "user_wasted_hours_report.%s" % (self.end_time.split(" ")[0].replace("/", "-"))
        f = open(fn, "w")
        f.write(text)
        f.close()
        emails = ""
        if self.is_test:
            emails = self.config.get("email", "test_to").split(", ")
        else:
            pass
            # emails=self.config.get("email", "%s_email" % (self.vo.lower())).split(",")+self.config.get("email", "test_to").split(",")
        TextUtils.sendEmail(([], emails), "%s Wasted Hours on the GPGrid (%s - %s)" % ("FIFE", self.start_time, self.end_time), {"html": text},  ("Gratia Operation", "tlevshin@fnal.gov"), "smtp.fnal.gov")
        # os.unlink(fn)


def parse_opts():
        """Parses command line options"""

        usage = "Usage: %prog [options]"
        parser = optparse.OptionParser(usage)
        parser.add_option("-c", "--config", dest="config", type="string", help="report configuration file (required)")
        parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                          help="print debug messages to stdout")
        parser.add_option("-s", "--start", type="string", dest="start",
                          help="report start date YYYY/MM/DD HH:MM:DD (required)")
        parser.add_option("-e", "--end", type="string", dest="end", help="report end date YYYY/MM/DD")
        parser.add_option("-d", "--dryrun", action="store_true", dest="is_test", default=False,
                          help="send emails only to testers")

        opts, args = parser.parse_args()
        Configuration.checkRequiredArguments(opts, parser)
        return opts, args


if __name__ == "__main__":
    opts, args = parse_opts()
    try:
        config = Configuration.Configuration()
        config.configure(opts.config)
        report = WastedHoursReport(config, opts.start, opts.end, opts.is_test, opts.verbose)
        report.generate()
        report.send_report()
    except:
        print >> sys.stderr, traceback.format_exc()
        sys.exit(1)
    sys.exit(0)
