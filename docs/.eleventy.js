const markdownIt = require("markdown-it");
const markdownItAttrs = require("markdown-it-attrs");
const markdownItToc = require("markdown-it-toc-done-right");

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("assets");

  const md = markdownIt({ html: true, linkify: true })
    .use(markdownItAttrs)
    .use(markdownItToc, {
      containerClass: "table-of-contents",
      listType: "ul",
      level: [2, 3],
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
