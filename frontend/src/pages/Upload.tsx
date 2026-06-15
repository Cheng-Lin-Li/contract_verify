// Upload a contract + deal sources, kick off verification, poll, then route to the report.
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useJobPolling } from "../hooks/useContract";

export default function Upload() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [contract, setContract] = useState<File | null>(null);
  const [sources, setSources] = useState<FileList | null>(null);
  const [contractType, setContractType] = useState("services");
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJobPolling(jobId);

  if (job?.status === "completed") navigate(`/report/${job.contract_id}`);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!contract) return;
    const form = new FormData();
    form.append("contract", contract);
    if (sources) Array.from(sources).forEach((f) => form.append("sources", f));
    const created = await api.uploadContract(form, contractType);
    setJobId(created.job_id);
  }

  const running = !!jobId && job?.status !== "failed";

  return (
    <div className="max-w-xl">
      <h1 className="mb-4 text-xl font-semibold">{t("upload.title")}</h1>
      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium">{t("upload.contract")}</label>
          <input type="file" accept=".pdf,.docx,.txt"
                 onChange={(e) => setContract(e.target.files?.[0] ?? null)}
                 className="mt-1 block w-full text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium">{t("upload.sources")}</label>
          <input type="file" multiple accept=".pdf,.docx,.eml,.txt,.msg"
                 onChange={(e) => setSources(e.target.files)}
                 className="mt-1 block w-full text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium">{t("upload.contractType")}</label>
          <input value={contractType} onChange={(e) => setContractType(e.target.value)}
                 className="mt-1 w-full rounded border border-slate-300 px-2 py-1" />
        </div>
        <button disabled={!contract || running}
                className="rounded bg-ink px-4 py-2 text-white disabled:opacity-50">
          {running ? t("upload.running") : t("upload.submit")}
        </button>
        {job?.status === "failed" && <p className="text-sm text-red-600">{job.error}</p>}
      </form>
    </div>
  );
}
