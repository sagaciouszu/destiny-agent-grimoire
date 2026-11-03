const markdownIt = require("markdown-it");
const markdownItAnchor = require("markdown-it-anchor");

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("assets");

  const md = markdownIt({ html: true, linkify: true }).use(markdownItAnchor, {
    slugify: (value) => value
      .trim()
      .toLowerCase()
      .replace(/\./g, "-")
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-"),
    permalink: markdownItAnchor.permalink.linkInsideHeader({
      symbol: "#",
      placement: "after",
      class: "heading-anchor",
      ariaHidden: false,
      renderAttrs: () => ({ "aria-label": "Permalink to this section" }),
    }),
  });
  eleventyConfig.setLibrary("md", md);

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
      layouts: "_layouts",
      data: "_data",
    },
    pathPrefix: "/destiny-agent-grimoire/",
    templateFormats: ["md", "njk"],
  };
};
