# Demo recording

**Try the demo** replays `ndi-demo.json` from this folder: a real NDI + Drex run, recorded from the desk itself. Without that file, the demo falls back to the original LULU earnings-call replay.

## Record it

1. Run the desk locally with your key and open **FILINGS · NDI**.
2. Drop the filing. For the LULU case, use the Q2 FY2026 earnings release: Exhibit 99.1 of lululemon's 8-K filed Sept 3, 2026, from [SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001397187&type=8-K). Print the exhibit to PDF if EDGAR only has HTML.
3. Hit **Read filings**, check the facts against their pages, then **Send to signal gate →** on the LULU signal and **Run gate**.
4. Back on the filings tab, hit **Export run ⤓**. Save the download here as `demo/ndi-demo.json`.

The file holds the parsed markdown, the extracted facts with their page citations and crop images, the credits and timings of each job, and the Drex gate response. It contains no API key. SEC filings are public documents, so the parsed text can ship with the repo.
