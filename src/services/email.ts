import nodemailer from 'nodemailer';

class EmailService {
  private transporter: nodemailer.Transporter;

  constructor() {
    this.transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.GMAIL_EMAIL,
        pass: process.env.GMAIL_APP_PASSWORD,
      },
    });
  }

  async sendOTP(email: string, otp: string): Promise<void> {
    try {
      const mailOptions = {
        from: process.env.GMAIL_EMAIL,
        to: email,
        subject: 'Verification Code for CMS Registration',
        html: `
          <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #023C40;">CMS Registration Verification</h2>
            <p>Your verification code is:</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #023C40; margin: 20px 0;">
              ${otp}
            </div>
            <p>This code will expire in ${process.env.OTP_EXPIRY_MINUTES || 5} minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
          </div>
        `,
      };

      await this.transporter.sendMail(mailOptions);
      console.log(`OTP sent to ${email}`);
    } catch (error) {
      console.error('Email send error:', error);
      throw new Error('Failed to send email');
    }
  }
}

export const emailService = new EmailService();