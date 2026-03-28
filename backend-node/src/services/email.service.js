/**
 * RAG Platform — Email Service (Nodemailer + Gmail)
 * Handles single and bulk email sending.
 * Called by workspace routes when Python returns email_mode in the query response.
 */

const nodemailer = require("nodemailer");

// ── Create reusable transporter ───────────────────────────────────────────────
const createTransporter = () => {
  const user = process.env.GMAIL_ADDRESS;
  const pass = process.env.GMAIL_APP_PASSWORD;

  if (!user || !pass) {
    throw new Error(
      "Gmail not configured. Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to your .env file."
    );
  }

  return nodemailer.createTransport({
    service: "gmail",
    auth: { user, pass },
  });
};

// ── HTML Template ─────────────────────────────────────────────────────────────
const buildHTML = (subject, body) => {
  // Convert plain text line breaks and basic markdown to HTML
  let htmlBody = body
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .split("\n\n")
    .map((p) => `<p style="margin:0 0 14px 0;">${p.replace(/\n/g, "<br>")}</p>`)
    .join("");

  const date = new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:36px 0;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:580px;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0D1B2A 0%,#4361EE 100%);padding:28px 36px 24px;">
            <div style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">
              &#11041; RAG Platform
            </div>
            <div style="color:#94A3B8;font-size:12px;margin-top:3px;">
              AI Document Intelligence
            </div>
          </td>
        </tr>

        <!-- Subject banner -->
        <tr>
          <td style="background:#4361EE;padding:12px 36px;">
            <div style="color:#ffffff;font-size:14px;font-weight:600;">${subject}</div>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:28px 36px 24px;color:#1E293B;font-size:14px;line-height:1.75;">
            ${htmlBody}
          </td>
        </tr>

        <!-- Divider -->
        <tr>
          <td style="padding:0 36px;">
            <hr style="border:none;border-top:1px solid #E2E8F0;margin:0;">
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:18px 36px 24px;">
            <div style="color:#94A3B8;font-size:11px;line-height:1.6;">
              Sent by <strong style="color:#4361EE;">RAG Platform</strong>
              &nbsp;&middot;&nbsp; ${date}
              &nbsp;&middot;&nbsp; This is an automated message.
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
};

// ── Send a single email ───────────────────────────────────────────────────────
const sendSingleEmail = async ({ to, subject, body }, pdfBuffer = null, pdfFilename = null) => {
  console.log("[NODEMAILER] Creating transporter with:", process.env.GMAIL_ADDRESS ? "✓ GMAIL_ADDRESS set" : "✗ GMAIL_ADDRESS missing");
  console.log("[NODEMAILER] App password:", process.env.GMAIL_APP_PASSWORD ? "✓ set" : "✗ MISSING");

  const transporter = createTransporter();
  const senderName  = `RAG Platform <${process.env.GMAIL_ADDRESS}>`;

  const mailOptions = {
    from:    senderName,
    to,
    subject,
    text:    body,
    html:    buildHTML(subject, body),
  };

  // Attach PDF report if provided
  if (pdfBuffer && pdfFilename) {
    mailOptions.attachments = [{
      filename:    pdfFilename,
      content:     pdfBuffer,
      contentType: "application/pdf",
    }];
    console.log("[NODEMAILER] PDF attached:", pdfFilename);
  }

  console.log("[NODEMAILER] Sending to:", to);
  const info = await transporter.sendMail(mailOptions);
  console.log("[NODEMAILER] ✓ Message sent! ID:", info.messageId);
  return { success: true, to };
};

// ── Send bulk emails ──────────────────────────────────────────────────────────
const sendBulkEmails = async (recipients, pdfBuffer = null, pdfFilename = null) => {
  const transporter = createTransporter();
  const senderName  = `RAG Platform <${process.env.GMAIL_ADDRESS}>`;

  let sent = 0, failed = 0;
  const errors = [];

  for (const { to, subject, body } of recipients) {
    try {
      const mailOptions = {
        from:    senderName,
        to,
        subject,
        text:    body,
        html:    buildHTML(subject, body),
      };
      if (pdfBuffer && pdfFilename) {
        mailOptions.attachments = [{
          filename:    pdfFilename,
          content:     pdfBuffer,
          contentType: "application/pdf",
        }];
      }
      await transporter.sendMail(mailOptions);
      sent++;
    } catch (err) {
      failed++;
      errors.push(`${to}: ${err.message}`);
    }
  }

  return { sent, failed, errors: errors.slice(0, 5) };
};

module.exports = { sendSingleEmail, sendBulkEmails };