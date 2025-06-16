export function generateOTP(length: number = 6): string {
  // For development, use fixed OTP if specified
  if (process.env.NODE_ENV === 'development' && process.env.OTP_SECRET) {
    return process.env.OTP_SECRET;
  }
  
  const digits = '0123456789';
  let otp = '';
  
  for (let i = 0; i < length; i++) {
    otp += digits[Math.floor(Math.random() * 10)];
  }
  
  return otp;
}