export type UserRole = "CANDIDATE" | "HR_REVIEWER" | "ADMIN";

export type ApplicationStatus =
  | "SUBMITTED"
  | "IDENTITY_VERIFIED"
  | "PROVISIONAL_APPROVED"
  | "FINAL_APPROVED"
  | "COMPLETED"
  | "REJECTED";

export type VerificationStatus = "SUCCESS" | "FAILED" | "PENDING";

export type DocumentType =
  | "PROVISIONAL_OFFER"
  | "FINAL_OFFER"
  | "COMPLETION_CERTIFICATE";

export interface User {
  user_id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthStatusResponse {
  message: string;
  user: User;
}

export interface InternProfile {
  profile_id: string;
  user_id: string;
  full_name: string;
  phone_number: string;
  college_name: string;
  internship_role: string;
  start_date: string;
  end_date: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  pin_code?: string | null;
  work_mode?: string | null;
  work_schedule?: string | null;
  reporting_manager?: string | null;
  application_status: ApplicationStatus;
  created_at: string;
  updated_at: string;
}

export interface InternProfileCreatePayload {
  full_name: string;
  phone_number: string;
  college_name: string;
  internship_role: string;
  start_date: string;
  end_date: string;
  address?: string;
  city?: string;
  state?: string;
  pin_code?: string;
  work_mode?: string;
  work_schedule?: string;
  reporting_manager?: string;
}

export interface StageDecisionPayload {
  target_status:
    | "PROVISIONAL_APPROVED"
    | "FINAL_APPROVED"
    | "COMPLETED"
    | "REJECTED";
  remarks: string;
  internship_role?: string;
  start_date?: string;
  end_date?: string;
  work_mode?: string;
  work_schedule?: string;
  reporting_manager?: string;
  address?: string;
  city?: string;
  state?: string;
  pin_code?: string;
}

export interface KYCInitiateOTPResponse {
  session_token: string;
  gateway_provider: string;
  masked_destination: string;
  expires_in_seconds: number;
  message: string;
}

export interface VerificationLog {
  verification_id: string;
  profile_id: string;
  gateway_provider: string;
  transaction_reference: string;
  status: VerificationStatus;
  verified_at: string;
}

export interface KYCVerifyOTPResponse {
  message: string;
  application_status: ApplicationStatus;
  verification: VerificationLog;
}

export interface DocumentMetadata {
  document_id: string;
  profile_id: string;
  document_type: DocumentType;
  verification_code: string;
  issuer_remarks?: string | null;
  is_valid: boolean;
  checksum_sha256: string;
  admin_approved_by: string;
  generated_at: string;
}

export interface StageDecisionResponse {
  message: string;
  profile_id: string;
  previous_status: ApplicationStatus;
  new_status: ApplicationStatus;
  idempotency_key: string;
  document: DocumentMetadata | null;
}

export interface SignedUrlResponse {
  document_id: string;
  document_type: DocumentType;
  verification_code: string;
  download_url: string;
  expires_at: number;
  checksum_sha256: string;
}

export interface CertificateVerificationResponse {
  verified: boolean;
  validity_status: "VALID" | "REVOKED";
  verification_code: string;
  document_type: DocumentType;
  intern_name: string;
  internship_designation: string;
  college_name: string;
  start_date: string;
  end_date: string;
  duration_display: string;
  work_mode?: string | null;
  reporting_manager?: string | null;
  issued_at: string;
  issuer_remarks?: string | null;
  checksum_sha256: string;
}

export interface AuditLog {
  log_id: string;
  actor_id: string | null;
  action: string;
  target_entity: string;
  ip_address: string;
  details: Record<string, unknown>;
  timestamp: string;
}