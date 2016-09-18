#!/bin/python
#!coding=utf-8
import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

class mailError(Exception):
    pass

class mailSender(object):
    """
      " mailSender class
      " this function is send out our html email
    """
    def __init__(self,server_host="localhost",m_user="", m_passwd=""):
        self.mail_host=server_host
        self.sender=""
        self.receivers=[]
        self.message=MIMEMultipart('alternative')
        self.subject=""
        self.mail_user=m_user
        self.mail_passwd=m_passwd

    def get_sender(self):
        return self.sender

    def get_receiver(self):
        return self.receivers

    def get_message(self):
        return self.message.as_string()

    #@sender sender mail string
    def set_sender(self,sender):
        if isinstance(sender, basestring):
            self.sender=sender
        else:
            err_sender_msg= "Error: sender format error!"
            raise mailError(err_sender_msg)

    """
      " receiver is a mail list which is split by ';'
    """
    def set_receiver(self,receiver):
        if isinstance(receiver,basestring):
            self.receivers=receiver.split(';')
        else:
            err_receiver_msg="Error: receiver format error"
            raise mailError(err_receiver_msg)

    def set_agent_mail(self, mhost, muser, m_passwd):
        self.mail_host = mhost
        self.mail_user = muser
        self.mail_passwd = m_passwd

    def set_mail_msg(self,subject, msg, att_file_list=None):
        self.message['Subject'] = formataddr((str(Header(subject,'utf-8')),'%s' % subject))
        #self.message['To'] = Header("All_Pblaze4",'utf-8')
        #self.message['From'] = Header("QA test manager",'utf-8')
        self.message['To'] = formataddr((str(Header('QA ALL','utf-8')),'%s' % self.receivers))
        self.message['From'] = formataddr((str(Header('hotplug','utf-8')),'%s' % self.sender))
        self.message.preamble = """
            Your mail reader does not support the report format.
            please connect us <yazhou.zhao@memblaze.com> by email"""

        """
          "mail body by mail msg format (default:html)
        """
        self.message.attach(self.format_mailmsg(msg,'html'))

        """
          "this is extra context follow mail msg body
        """
        self.message.attach(MIMEText("this is QA test report....",'plain','utf-8'))

        if att_file_list != None:
            if type(att_file_list) == list:
                for att_file in att_file_list:
                    att_iter = MIMEText(open(att_file,'rb').read(), 'base64','utf-8')
                    att_iter['Content-Type'] = 'application/octet-stream'
                    att_iter["Content-Disposition"] = 'attachment; filename="%s" ' % os.path.basename(os.path.abspath(__file__))
                    self.message.attach(att_iter)

    def format_mailmsg(self,msg, msg_type):
        if msg_type == 'html':
            #record the MIME type text/html
            return MIMEText(msg,'html',_charset='gb2312')

    def send_email(self,sender, receivers, subject, msg, att_file_list=None, mail_agent_flag=0):
        if mail_agent_flag == 0:
            smtpObj = smtplib.SMTP('localhost')
            try:
                self.set_sender(sender)
                self.set_receiver(receivers)
                self.set_mail_msg(subject,msg,att_file_list)
                smtpObj.sendmail(self.sender, self.receivers, self.message.as_string())

            except mailError:
                print "send mail error!!"
                sys.exit(1)
            else:
                print "send mail OK"
        else:
            smtpObj = smtplib.SMTP()
            try:
                self.set_sender(sender)
                self.set_receiver(receivers)
                self.set_mail_msg(subject,msg,att_file_list)
                smtpObj.connect(self.mail_host,25)
                smtpObj.starttls()
                smtpObj.login(self.mail_user, self.mail_passwd)
                smtpObj.sendmail(self.sender, self.receivers, self.message.as_string())
                smtpObj.quit()
            except mailError:
                print "send agent mail error!!"
                sys.exit(1)
            except Exception as e:
                print "send agent mail error!!"
                print e
                sys.exit(1)
            else:
                print "send agent mail OK"

if __name__ == "__main__":
    mail_sender = mailSender('localhost')
    to = "yazhou.zhao@memblaze.com;yongfeng.zhou@memblaze.com;yang.yuan@memblaze.com"
    #to = "yazhou.zhao@memblaze.com"
    #FROM = "yazhou12315@163.com"
    FROM = "yazhou.zhao@memblaze.com"
    subject="test smtp mail"
    msg="""
    <head>
     <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
     <title>html test</title>
     <style type="text/css" media="screen">
       table{
           background-color: #AAD373;
           empty-cells:hide;
       }
       thead{
           color:##AAC260;
       }
       td.cell{
           background-color: white;
       }
     </style>
    </head>
    <body>
      <table style="border;blue 1px solid;">
        <caption>Pblaze4 test report</caption>
        <thead>
        <tr><td class="cell">Test Item</td><td class="cell">Case Name</td>
        <td class="cell">Os type</td><td class="cell">status</td>
        <td class="cell">Comments</td></tr>
        </thead>
        <tr><td class="cell">HotPlug </td><td class="cell"></td>
        <td class="cell"></td><td class="cell"></td>
        <td class="cell"></td></tr>

      </table>
    </body>
    """

    mail_sender.send_email(FROM, to , subject, msg)

