import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
def kirimEmail(pesan):
	
	fromaddr = "akiyar18@gmail.com"
	toaddr = ["akiyar18@gmail.com", "akiyar@apps.ipb.ac.id", "imas.sitanggang@apps.ipb.ac.id"]
	print("Mengirim email ke " + str(toaddr))
	msg = MIMEMultipart()
	# msg['From'] = fromaddr
	# msg['To'] = toaddr
	msg['Subject'] = "Notifikasi SisKPL (Sistem Otomatisasi Klasifikasi Tutupan Lahan)"
	
	body = pesan
	msg.attach(MIMEText(body, 'plain'))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login(fromaddr, "Rickss12")
	text = msg.as_string()
	#text = pesan
	server.sendmail(fromaddr, toaddr, text)
	print("Email telah dikirim ke " + str(toaddr))
	server.quit()