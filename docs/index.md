---
layout: default
title: Destiny Agent Grimoire
description: One canonical Destiny lore archive and the independent agents built from it.
---

<section class="hero">
  <p class="kicker">Canonical Destiny lore · agent interface</p>
  <h1>Destiny Agent Grimoire</h1>
  <p class="lede">
    One archive of Destiny lore, built to be read by people and queried by agents.
    Every line carries its source, and every quote can be checked before it is used.
  </p>
  <div class="hero-actions">
    <a class="button button-primary" href="{{ '/grimoire/install/' | url }}">Install the Grimoire</a>
    <a class="button" href="{{ '/agents/' | url }}">Meet the agents</a>
  </div>
</section>

<section class="categories" aria-label="Explore the project">
  <article class="category">
    <span class="category-index" aria-hidden="true">01</span>
    <div>
      <h2>The Grimoire</h2>
      <p>
        A single SQLite archive with full-text search, provenance for every row,
        and a quote-verification layer. It is the canon that every agent reads.
      </p>
      <div class="category-links">
        <a href="{{ '/grimoire/' | url }}">What it contains</a>
        <a href="{{ '/grimoire/install/' | url }}">Install and query it</a>
      </div>
    </div>
  </article>

  <article class="category">
    <span class="category-index" aria-hidden="true">02</span>
    <div>
      <h2>Agents &amp; Instructions</h2>
      <p>
        The Drifter and Eris Morn are independent character agents. They keep
        separate voices and memory, share only the Grimoire, and can consult each
        other through read-only copies.
      </p>
      <div class="category-links">
        <a href="{{ '/agents/' | url }}">How the series works</a>
        <a href="{{ '/agents/install/' | url }}">Deploy an agent</a>
      </div>
    </div>
  </article>

  <article class="category">
    <span class="category-index" aria-hidden="true">03</span>
    <div>
      <h2>Troubleshooting</h2>
      <p>
        Symptoms, causes and fixes for the database, the MCP server, agent
        deployment and quote checks.
      </p>
      <div class="category-links">
        <a href="{{ '/troubleshooting/' | url }}">Open the troubleshooting guide</a>
      </div>
    </div>
  </article>
</section>
