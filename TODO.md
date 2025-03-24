- concurrency
- amalgamate or split
- txt output or formatted output
- change defaults? (Yes, No, Stop Asking)
- handle direct passing URL, options

- Sitemap (with depth and limits)
-
- in console, alias link

- youtube support
  - - timecode? sections?

-- youtube formats

- Raw -- transcript (no timecode, most basic metadata for organization), output is .txt format
- Complete - include all metadata and descriptions, output is .md
- Chapters -- Full transcript, organized by chapters if available, output is .md - yt-dlp --dump-json "https://www.youtube.com/watch?v=5cJuDFmtbgA" | jq --raw-output '.chapters[] | "\(.start_time) - \(.title)"' - chapter data might not be available - (base) danhilse@Mac Desktop % yt-dlp --dump-json "https://www.youtube.com/watch?v=5RoRCbaMJBg" | jq --raw-output ".chapters[].start_time"
  jq: error (at <stdin>:1): Cannot iterate over null (null) - requires the timecodes from the transcript to organize into chapter (## markdown titles) and then stripping the timecodes for clean formatting of transcript
