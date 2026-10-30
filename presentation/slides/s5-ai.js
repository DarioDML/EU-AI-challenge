/* Slide · How we used AI (4:25-4:45), explainable in 20 seconds. Owner: agent 6.
   Source of truth: the team's AI sheet (Annex 7). Tools: Claude, Gemini, ChatGPT, Perplexity, NotebookLM.
   Takeaways: speed (communication dashboard and shelter-matching system in two days), a catch (AI treated missing flood
   depth as dry; caught in code review, missing depth now stays "unknown"), verification (checked twice, every claim
   traced to its original source, unconfirmed sources removed). No names, no personal data. */
(function () {
  'use strict';
  const TEAM = 'Team 1';
  Deck.register({
    id: 's5ai', order: 5.5, title: 'How we used AI', steps: 3, time: [265, 285],
    notes: {
      title: 'How we used AI',
      script: 'AI let us build this tool in two days, which we could not have done by hand. It also made mistakes and missed data mismatches between our sources. We caught and fixed them. Every result was checked twice, and every source traced.',
      notes: [
        'Speed: AI helped us build the communication dashboard and the shelter-matching system in two days.',
        'It got something wrong: missing flood-depth values were treated as dry (safe). Caught in code review; missing depth now stays "unknown".',
        'Checked twice: AI against a checklist, and by hand against the raw data. Every claim in the brief traced to its original source; sources we could not confirm were removed.',
        'Tools used: Claude, Gemini, ChatGPT, Perplexity, NotebookLM.',
      ],
    },
    html: `
      <div class="ai-left">
        <span class="ai-rule" data-b="0"></span>
        <h2 class="h2 ai-title" data-b="0">AI built it fast.<br>We checked it.</h2>
        <ol class="ai-rows">
          <li class="ai-row r1" data-b="0"><span class="ai-no">01</span><span class="ai-t">Tool built in two days.</span></li>
          <li class="ai-row r2" data-b="1"><span class="ai-no">02</span><span class="ai-t">Caught: AI mistakes and data mismatches.</span></li>
          <li class="ai-row r3" data-b="2"><span class="ai-no">03</span><span class="ai-t">Every source traced.</span></li>
        </ol>
      </div>
      <div class="ai-track" data-b="0" aria-hidden="true">
        <i class="ai-line"></i><i class="ai-prog"></i>
        <i class="ai-n n1"><b></b></i><i class="ai-n n2"><b></b></i><i class="ai-n n3"><b></b></i>
        <span class="ai-lb lb1">build</span><span class="ai-lb lb2">catch</span><span class="ai-lb lb3">check</span>
        <i class="ai-dot"></i>
      </div>
      <p class="ai-tools" data-b="0">Claude · Gemini · ChatGPT · Perplexity · NotebookLM</p>
      <p class="ai-team" data-b="0">${TEAM}</p>`,
  });
})();
