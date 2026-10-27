"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  Lock,
  KeyRound,
  AlertCircle,
  CheckCircle2,
  X,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { KYCInitiateOTPResponse, KYCVerifyOTPResponse } from "@/types";

interface KycVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onVerified: (result: KYCVerifyOTPResponse) => void;
}

export function KycVerificationModal({
  isOpen,
  onClose,
  onVerified,
}: KycVerificationModalProps) {
  const [step, setStep] = useState<"INITIATE" | "OTP">("INITIATE");
  const [idType, setIdType] = useState<"AADHAAR" | "PAN" | "PASSPORT">("AADHAAR");
  const [idNumber, setIdNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [sessionData, setSessionData] = useState<KYCInitiateOTPResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleInitiateOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await apiClient.post<KYCInitiateOTPResponse>("/kyc/initiate-otp", {
        id_type: idType,
        id_number: idNumber.trim(),
      });
      // Immediately clear raw government ID from component state (Data Minimization)
      setIdNumber("");
      setSessionData(data);
      setStep("OTP");
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to initiate KYC OTP session."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionData) return;
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await apiClient.post<KYCVerifyOTPResponse>("/kyc/verify-otp", {
        session_token: sessionData.session_token,
        otp: otp.trim(),
      });
      setOtp("");
      onVerified(data);
      onClose();
    } catch (err) {
      setError(extractErrorMessage(err, "Invalid OTP code. Please try again."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="kyc-modal-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white border border-slate-200 shadow-xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="h-5 w-5 text-sky-400" />
            <div>
              <h2 id="kyc-modal-title" className="text-sm font-semibold">
                Government ID Verification Gateway
              </h2>
              <p className="text-[11px] text-slate-300">
                Zero-Retention Cryptographic KYC • TLS 1.3
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Privacy & Data Minimization Notice */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-3.5 text-xs text-slate-600 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-800">
              <Lock className="h-3.5 w-3.5 text-brand-600" />
              <span>Section 5.1 Data Minimization Guarantee</span>
            </div>
            <p className="leading-relaxed">
              Your raw ID number is processed strictly in volatile memory to compute a one-way{" "}
              <span className="font-mono text-[11px] text-slate-800">HMAC-SHA256</span> reference
              hash and is immediately discarded. No raw digits are ever written to logs or tables.
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2.5 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800">
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {step === "INITIATE" ? (
            <form onSubmit={handleInitiateOtp} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Document Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(["AADHAAR", "PAN", "PASSPORT"] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        setIdType(type);
                        setError(null);
                      }}
                      className={`py-2 px-3 rounded-md text-xs font-medium border transition-colors ${
                        idType === type
                          ? "bg-slate-900 text-white border-slate-900"
                          : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label
                  htmlFor="kyc-id-input"
                  className="block text-xs font-medium text-slate-700 mb-1.5"
                >
                  {idType === "AADHAAR"
                    ? "12-Digit Aadhaar Number"
                    : idType === "PAN"
                    ? "10-Character PAN Number"
                    : "Passport Number"}
                </label>
                <input
                  id="kyc-id-input"
                  type="text"
                  required
                  value={idNumber}
                  onChange={(e) => setIdNumber(e.target.value)}
                  placeholder={
                    idType === "AADHAAR"
                      ? "e.g. 4321-8765-2109"
                      : idType === "PAN"
                      ? "e.g. ABCDE1234F"
                      : "e.g. Z1234567"
                  }
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-md text-xs font-medium text-slate-700 border border-slate-300 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !idNumber.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Requesting OTP...
                    </>
                  ) : (
                    <>
                      Send Verification OTP
                      <ArrowRight className="h-3.5 w-3.5" />
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-900">
                <div className="flex items-center gap-1.5 font-semibold">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span>OTP Dispatched ({sessionData?.gateway_provider} Gateway)</span>
                </div>
                <p className="mt-1 text-emerald-800">
                  Sent to registered mobile{" "}
                  <span className="font-mono font-semibold">
                    {sessionData?.masked_destination}
                  </span>
                  . (For local MOCK gateway testing, enter OTP:{" "}
                  <span className="font-mono font-bold underline">123456</span>)
                </p>
              </div>

              <div>
                <label
                  htmlFor="kyc-otp-input"
                  className="block text-xs font-medium text-slate-700 mb-1.5"
                >
                  6-Digit One-Time Password (OTP)
                </label>
                <div className="relative">
                  <KeyRound className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="kyc-otp-input"
                    type="text"
                    inputMode="numeric"
                    pattern="\d{6}"
                    maxLength={6}
                    required
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    placeholder="123456"
                    className="w-full rounded-md border border-slate-300 pl-9 pr-3 py-2 text-sm font-mono tracking-widest text-slate-900 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setStep("INITIATE");
                    setError(null);
                  }}
                  className="text-xs font-medium text-slate-600 hover:text-slate-900"
                >
                  &larr; Change ID Document
                </button>
                <button
                  type="submit"
                  disabled={submitting || otp.length !== 6}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Verifying Token...
                    </>
                  ) : (
                    <>
                      Verify &amp; Seal Identity
                      <ShieldCheck className="h-3.5 w-3.5" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}