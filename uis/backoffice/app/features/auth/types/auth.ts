export type AuthProfile = {
  id: string;
  user_id: string;
  name: string;
  phone: string;
  address: string;
};

export type AuthUser = {
  email: string;
  role: "admin" | "manager" | "user";
  profile: AuthProfile;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  address?: string;
};

export type RegisterRequestPayload = {
  email: string;
  password: string;
  name: string;
  phone: string;
  address: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type ForgotPasswordPayload = {
  email: string;
};

export type ResetPasswordPayload = {
  token: string;
  new_password: string;
};

export type MessageResponse = {
  detail: string;
};