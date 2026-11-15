// Optional demo recording for the walkthrough scripts (P7-T07 backup recording).
//   RECORD_DIR=<folder>  → each browser context saves a .webm video there
//   SLOW_MO=<ms>         → slow every action down so a viewer can follow
// Unset = scripts run exactly as before.
export const launchOpts = { channel: "msedge", slowMo: Number(process.env.SLOW_MO || 0) };
export const rec = (size) => (process.env.RECORD_DIR ? { recordVideo: { dir: process.env.RECORD_DIR, size } } : {});
