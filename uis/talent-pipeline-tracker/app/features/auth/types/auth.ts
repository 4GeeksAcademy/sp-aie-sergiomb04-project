export type AuthProfile = {
  id: string;
  user_id: string;
  name: string;
  phone: string;
  address: string;
};

export type AuthUser = {
  email: string;
  role: string;
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

export type ProfileUpdatePayload = {
  name: string;
  phone: string;
  address: string;
};
