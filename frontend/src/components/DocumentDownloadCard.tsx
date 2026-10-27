"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  ShieldCheck,
  Loader2,
  Check,
  Clock,
  Copy,
  ExternalLink,
  MessageSquareQuote,
} from "lucide-react";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { DOCUMENT_TYPE_LABELS, formatDateTime } from "@/lib/utils";
import { DocumentMetadata, SignedUrlResponse } from "@/types";

interface DocumentDownloadCardProps {
  doc: DocumentMetadata;
}

export function DocumentDownloadCard({ doc }: DocumentDownloadCardProps) {
  const [downloading, setDownloading] = useState(false);
  const [signedMeta, setSignedMeta] = useState<SignedUrlResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const labelInfo = DOCUMENT_TYPE_LABELS[doc.document_type] || {
    title: doc.document_type,
    subtitle: "Encrypted Official CREYOTECH PDF Document",
  };

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(doc.verification_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard errors
    }
  };

  const handleSecureDownload = async () => {
    setError(null);
    setDownloading(true);
    try {
      const { data: signed } = await apiClient.post<SignedUrlResponse>(
        `/documents/${doc.document_id}/signed-url`
      );
      setSignedMeta(signed);

      const pdfResp = await apiClient.get<Blob>(
        signed.download_url.replace(/^\/api\/v1/, ""),
        { responseType: "blob" }
      );

      const blob = new Blob([pdfResp.data], { type: "application/pdf" });
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `CREYOTECH_${doc.document_type.toLowerCase()}_${doc.verification_code}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to download decrypted document."));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="rounded-xl bg-white border border-slate-200 p-4 sm:p-5 shadow-2xs hover:border-slate-300 transition-all space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-700 shrink-0">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-semibold text-slate-900">{labelInfo.title}</h4>
              <span
                className={`text-[10px] font-mono font-semibold uppercase px-2 py-0.5 rounded border ${
                  doc.is_valid
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : "bg-rose-50 text-rose-800 border-rose-200"
                }`}
              >
                {doc.is_valid ? "VALID CREDENTIAL" : "REVOKED"}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{labelInfo.subtitle}</p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-[11px] text-slate-500">
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3 text-slate-400" />
                Issued: {formatDateTime(doc.generated_at)}
              </span>
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                <ShieldCheck className="h-3 w-3 text-emerald-600" />
                Fernet Encrypted at Rest
              </span>
            </div>
          </div>
        </div>

        {/* 12-Character Verification Code Pill */}
        <div className="flex items-center gap-1.5 self-start bg-slate-900 text-white px-3 py-1.5 rounded-lg border border-slate-800">
          <div className="text-left">
            <span className="block text-[9px] uppercase tracking-wider text-slate-400 leading-none">
              12-Char Verify Code
            </span>
            <span className="font-mono text-xs font-bold tracking-wider text-sky-300">
              {doc.verification_code}
            </span>
          </div>
          <button
            type="button"
            onClick={() => void handleCopyCode()}
            title="Copy 12-character verification code"
            className="ml-1.5 p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
          <Link
            href={`/verify?code=${doc.verification_code}`}
            title="Verify on Public Portal"
            className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* Issuing HR / Admin Comments */}
      {doc.issuer_remarks && (
        <div className="rounded-lg bg-amber-50/70 border border-amber-200/80 px-3.5 py-2.5 text-xs text-slate-800 flex items-start gap-2.5">
          <MessageSquareQuote className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-950 block text-[11px]">
              Issuing HR / Administrator Remarks:
            </span>
            <p className="text-slate-700 mt-0.5 leading-relaxed">{doc.issuer_remarks}</p>
          </div>
        </div>
      )}

      {/* Cryptographic Checksum & Download Bar */}
      <div className="rounded-lg bg-slate-50 border border-slate-200/80 px-3.5 py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
        <div className="min-w-0">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block">
            SHA-256 Checksum Integrity Seal
          </span>
          <p className="text-[11px] font-mono text-slate-700 truncate" title={doc.checksum_sha256}>
            {doc.checksum_sha256}
          </p>
        </div>

        <button
          type="button"
          onClick={() => void handleSecureDownload()}
          disabled={downloading}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold bg-slate-900 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors shrink-0"
        >
          {downloading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Decrypting PDF...
            </>
          ) : signedMeta ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              Download PDF Again
            </>
          ) : (
            <>
              <Download className="h-3.5 w-3.5" />
              Signed PDF Download
            </>
          )}
        </button>
      </div>

      {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
    </div>
  );
}