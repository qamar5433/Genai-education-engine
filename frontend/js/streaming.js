window.Streaming = class Streaming {
  /**
   * Consume a server-sent events stream from a fetch Response.
   * @param {Response} response The fetch Response object.
   * @param {Object} handlers Callbacks for events.
   * @param {Function} handlers.onToken Called for each data token received.
   * @param {Function} handlers.onDone Called when [DONE] is received or stream ends.
   * @param {Function} handlers.onError Called if a parsing error occurs.
   */
  static async consume(response, { onToken, onDone, onError }) {
    if (!response.ok) {
      if (onError) onError(new Error(`Server returned ${response.status}`));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        let lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;

          const dataStr = trimmed.substring(6).trim();
          if (dataStr === "[DONE]") {
            if (onDone) onDone();
            return;
          }

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.token && onToken) {
              onToken(parsed.token);
            } else if (parsed.error && onError) {
              onError(new Error(parsed.error));
            }
          } catch (e) {
            console.warn("Stream JSON parse error:", e, dataStr);
          }
        }
      }
      if (onDone) onDone();
    } catch (err) {
      if (onError) onError(err);
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Attempts to parse JSON, extracting it from markdown if needed, 
   * and optionally repairing truncated JSON.
   */
  static parseJSON(text) {
    try {
      const match = text.match(/(\[[\s\S]*\]|\{[\s\S]*\})/);
      const target = match ? match[0] : text;
      
      try {
        return JSON.parse(target);
      } catch (e) {
        return JSON.parse(this.repairJSON(target));
      }
    } catch (e) {
      console.error("Failed to parse/repair JSON:", e, text);
      throw e;
    }
  }

  /**
   * Closes unclosed brackets and quotes to handle truncated JSON streams.
   */
  static repairJSON(json) {
    let stack = [];
    let inString = false;
    let escaped = false;

    for (let i = 0; i < json.length; i++) {
      const char = json[i];
      if (escaped) {
        escaped = false;
        continue;
      }
      if (char === '\\') {
        escaped = true;
        continue;
      }
      if (char === '"') {
        inString = !inString;
        continue;
      }
      if (inString) continue;

      if (char === '[' || char === '{') {
        stack.push(char === '[' ? ']' : '}');
      } else if (char === ']' || char === '}') {
        if (stack.length > 0 && stack[stack.length - 1] === char) {
          stack.pop();
        }
      }
    }

    let repaired = json;
    if (inString) repaired += '"';
    while (stack.length > 0) {
      repaired += stack.pop();
    }
    return repaired;
  }
};
console.log("🚀 GENAI EDUCANTION ENGINE: Streaming Helper Loaded");
