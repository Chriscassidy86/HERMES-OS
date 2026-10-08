# HERMES Creative Studio

A local browser app for text-to-image and text-to-video experiments. It is separate from HERMES-OS trading services and does not read or change trading data.

## Start it

1. Install Python 3 if it is not already available.
2. Create an API key in your OpenAI developer account and make sure API billing is enabled. API charges are separate from a ChatGPT subscription.
3. Open PowerShell in the HERMES-OS folder and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\creative_studio\Start-CreativeStudio.ps1
   ```

4. Paste your API key at the hidden prompt, then open <http://127.0.0.1:8766> in your browser. Keep the PowerShell window open while using the studio. Press Ctrl+C there when you are finished.

The key is read in hidden input, held only by the running process, never placed in the page, and removed when the app stops. Generated images and videos are saved under `creative_studio/generated`. The server binds to localhost only. Image generation uses OpenAI's GPT Image API; video generation uses the Sora API. Video jobs can take several minutes and API usage may cost money.

If the port is already in use, set another local port before starting: `$env:CREATIVE_STUDIO_PORT = "8767"`.
