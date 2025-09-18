import poplib
import email
import ssl
import time
from email.header import decode_header

class EmailClient:
	def __init__(self):
		# 邮箱服务器信息 - 根据您的配置图片设置
		self.pop_host = 'popw.263.net'  # POP3收件服务器地址
		self.pop_port = 995  # POP3端口
		self.smtp_host = 'smtpw.263.net'  # SMTP发件服务器地址
		self.smtp_port = 465  # SMTP端口
		self.email_user = 'nie.jie@kotei.com.cn'  # 邮箱地址
		self.email_pass = '92795916'  # 263企业邮箱中的授权码
		
	def connect_pop3(self):
		"""连接到POP3服务器"""
		try:
			# 创建SSL上下文
			context = ssl.create_default_context()
			# 连接到POP3服务器
			mail = poplib.POP3_SSL(self.pop_host, self.pop_port, context=context)
			# 登录
			mail.user(self.email_user)
			mail.pass_(self.email_pass)
			print("成功连接到POP3服务器")
			return mail
		except Exception as e:
			print(f"连接POP3服务器失败: {e}")
			return None
	
	def get_emails(self, mail, num_emails=5):
		"""获取最新的几封邮件"""
		try:
			# 获取邮件数量和大小
			num_messages = len(mail.list()[1])
			print(f"邮箱中共有 {num_messages} 封邮件")
			
			# 获取最新的几封邮件
			start_index = max(1, num_messages - num_emails + 1)
			emails = []
			
			for i in range(start_index, num_messages + 1):
				try:
					# 获取邮件
					raw_email = b"\n".join(mail.retr(i)[1])
					# 解析邮件
					msg = email.message_from_bytes(raw_email)
					emails.append(self.parse_email(msg))
				except Exception as e:
					print(f"解析第 {i} 封邮件时出错: {e}")
					continue
			
			return emails
		except Exception as e:
			print(f"获取邮件失败: {e}")
			return []
	
	def parse_email(self, msg):
		"""解析邮件内容"""
		email_info = {}
		
		# 解码邮件主题
		subject = decode_header(msg['subject'])[0][0]
		if isinstance(subject, bytes):
			subject = subject.decode('utf-8', errors='ignore')
		email_info['subject'] = subject
		
		# 解码发件人
		from_ = msg.get('From', '')
		email_info['from'] = from_
		
		# 获取日期
		date = msg.get('Date', '')
		email_info['date'] = date
		
		# 获取邮件正文
		body = self.get_email_body(msg)
		email_info['body'] = body
		
		return email_info
	
	def get_email_body(self, msg):
		"""获取邮件正文"""
		body = ""
		
		if msg.is_multipart():
			# 邮件包含多个部分
			for part in msg.walk():
				content_type = part.get_content_type()
				content_disposition = part.get('Content-Disposition')
				
				if content_type == 'text/plain' and content_disposition is None:
					try:
						payload = part.get_payload(decode=True)
						if payload:
							body = payload.decode('utf-8', errors='ignore')
							break
					except Exception as e:
						print(f"解码邮件正文时出错: {e}")
		else:
			# 邮件不包含多个部分
			try:
				payload = msg.get_payload(decode=True)
				if payload:
					body = payload.decode('utf-8', errors='ignore')
			except Exception as e:
				print(f"解码邮件正文时出错: {e}")
		
		return body
	
	def display_emails(self, emails):
		"""显示邮件信息"""
		if not emails:
			print("没有找到邮件")
			return
		
		print(f"\n=== 最新 {len(emails)} 封邮件 ===")
		for i, email_info in enumerate(emails, 1):
			print(f"\n--- 邮件 {i} ---")
			print(f"主题: {email_info['subject']}")
			print(f"发件人: {email_info['from']}")
			print(f"日期: {email_info['date']}")
			print(f"正文预览: {email_info['body'][:200]}...")
			print("-" * 50)
	
	def auto_check_emails(self, interval=300):
		"""自动检查新邮件"""
		print(f"开始自动检查邮件，间隔 {interval} 秒")
		print("按 Ctrl+C 停止")
		
		try:
			while True:
				mail = self.connect_pop3()
				if mail:
					emails = self.get_emails(mail, 3)  # 获取最新3封邮件
					self.display_emails(emails)
					mail.quit()
				
				print(f"\n等待 {interval} 秒后再次检查...")
				time.sleep(interval)
				
		except KeyboardInterrupt:
			print("\n自动检查已停止")
		except Exception as e:
			print(f"自动检查出错: {e}")

def main():
	"""主函数"""
	client = EmailClient()
	
	print("邮箱客户端启动")
	print("1. 手动检查邮件")
	print("2. 自动检查邮件")
	
	choice = input("请选择操作 (1/2): ").strip()
	
	if choice == '1':
		# 手动检查邮件
		mail = client.connect_pop3()
		if mail:
			emails = client.get_emails(mail, 5)  # 获取最新5封邮件
			client.display_emails(emails)
			mail.quit()
	elif choice == '2':
		# 自动检查邮件
		interval = input("请输入检查间隔（秒，默认300）: ").strip()
		try:
			interval = int(interval) if interval else 300
		except ValueError:
			interval = 300
		client.auto_check_emails(interval)
	else:
		print("无效选择")

if __name__ == "__main__":
	main()


