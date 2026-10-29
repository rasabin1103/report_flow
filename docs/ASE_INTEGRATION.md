# Future ASE integration (not implemented)
ASE can remain the trusted orchestrator while ReportFlow stays independently reusable:
1. Authenticate the user within ASE.
2. Authorize access to the organization and dataset; check reporting entitlements.
3. Enforce tenant quotas/credits and reserve capacity before submitting work.
4. Upload dataset bytes and a versioned JSON config over a protected internal HTTP connection.
5. Receive a PDF response; handle validation/resource errors and charge only according to an explicit success policy.
6. Optionally store the PDF in ASE-managed Supabase Storage using server-side credentials and tenant-scoped access policies.
7. Associate storage key, config hash, source checksum, timestamp and generation status with the customer organization.
8. Reconcile reserved quotas, record auditing metadata without source data, and expose an authorized download through ASE.

Keep authentication/billing/organization lookup and storage credentials out of ReportFlow. Put gateway service authentication, tenant authorization and rate limits around the standalone service. No ASE, Supabase, billing or authentication integration is implemented here.
