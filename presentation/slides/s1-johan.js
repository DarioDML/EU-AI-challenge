/* Opening: independent survey shares, never inferred overlapping respondent groups.
   Source: Thieken et al. 2023, NHESS 23, 973-990, DOI 10.5194/nhess-23-973-2023. */
(function () {
  'use strict';
  const dots = (count, name) => `<div class="s1-dots" role="img" aria-label="${count} of 100 dots highlighted: ${name}">` +
    Array.from({ length: 100 }, (_, i) => `<i class="${i < count ? 'filled' : ''}" style="--dot-delay:${i * 2}ms"></i>`).join('') + '</div>';
  const source = 'Thieken et al. (2023), NHESS 23, 973-990, DOI 10.5194/nhess-23-973-2023. July 2021 floods; online survey, n = 1,315 flood-affected respondents.';
  Deck.register({
    id: 's1', order: 1, title: 'Meet Johan', steps: 4, time: [0, 45],
    notes: {
      title: 'Meet Johan',
      script: "Meet Johan, 11, a fictional resident of Bad Neuenahr-Ahrweiler. He has three questions. Am I in danger? How serious is it? Where should I go? " +
        "In July 2021, the water came at night. In a survey of flood-affected people, 29% in Rhineland-Palatinate received no warning. " +
        "Among warned respondents across both states, 85% did not expect very severe flooding, and 46% lacked knowledge on protective action. " +
        "A useful warning must reach Johan and help him act.",
      notes: [
        'Johan is a fictional character, aged 11, placed in Bad Neuenahr-Ahrweiler for the map story.',
        source,
        '29%: respondents in Rhineland-Palatinate who received no warning. The corresponding share for North Rhine-Westphalia was 35%.',
        '85% and 46%: separate percentages among warned respondents in the study of both states. They do not share the RP-only denominator of the 29% figure.',
        'Each grid normalises its own percentage to 100 dots. Dots are percentage points, not individual participants. No overlap between the two warned groups is inferred.',
        'Source checked against the published abstract on 30 October 2026: https://nhess.copernicus.org/articles/23/973/2023/',
      ],
    },
    html: `
      <div class="s1-art" aria-hidden="true">
        <figure class="s1-fig s1-solo"><img src="assets/johan/johan-solo.png" width="252" height="696" alt=""></figure>
        <figure class="s1-fig s1-think"><img src="assets/johan/johan-thinking-tight.png" width="413" height="1233" alt=""></figure>
      </div>
      <div class="s1-intro" data-b="0" data-b-out="1">
        <p class="kicker">14 July 2021</p>
        <h1 class="h-hero">Meet Johan</h1>
        <p class="lead">11 ? Bad Neuenahr-Ahrweiler</p>
        <p class="s1-micro">Fictional character</p>
      </div>
      <ol class="s1-qs" data-b="1" data-b-out="2" aria-label="Johan's three questions">
        <li><span>01</span><h2>Am I in danger?</h2></li>
        <li><span>02</span><h2>How serious is it?</h2></li>
        <li><span>03</span><h2>Where should I go?</h2></li>
      </ol>
      <div class="s1-unwarned" data-b="2" data-b-out="3">
        <div class="s1-unwarned-copy">
          <h2 class="h2">The water came<br>at night</h2>
          <div class="s1-rate s1-rate-large">29<span>%</span></div>
          <p class="s1-description">received no warning</p>
          <p class="s1-denom">Respondents in Rhineland-Palatinate</p>
        </div>
        <figure class="s1-unwarned-grid">
          ${dots(29, 'received no warning')}
          <figcaption>29 of every 100 percentage points</figcaption>
        </figure>
      </div>
      <div class="s1-warned" data-b="3">
        <h2 class="h2">Among those warned</h2>
        <p class="s1-denom">Warned respondents across both states</p>
        <div class="s1-comparison">
          <section class="s1-measure">
            <div class="s1-measure-copy"><div class="s1-rate">85<span>%</span></div><p class="s1-description">didn?t expect<br>very severe flooding</p></div>
            <figure>${dots(85, 'did not expect very severe flooding')}<figcaption>Share among warned respondents</figcaption></figure>
          </section>
          <section class="s1-measure">
            <div class="s1-measure-copy"><div class="s1-rate">46<span>%</span></div><p class="s1-description">lacked knowledge<br>on protective action</p></div>
            <figure>${dots(46, 'lacked knowledge on protective action')}<figcaption>Share among warned respondents</figcaption></figure>
          </section>
        </div>
        <p class="s1-grid-note">Each grid represents a separate percentage. Overlap between the groups is not shown.</p>
      </div>
      <p class="src s1-src" data-b="2">${source}<br>29%: Rhineland-Palatinate. 85% and 46%: warned respondents in Rhineland-Palatinate and North Rhine-Westphalia.</p>`,
  });
})();
