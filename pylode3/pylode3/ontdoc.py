import dominate
from dominate.tags import h2, h1, h4, style, link, meta, script, p, dl, strong, dt, dd
from utils import *
from typing import Dict

RDF_FOLDER = Path(__file__).parent / "rdf"


class OntDoc:
    def __init__(self, ontology: Union[Graph, Path, str]):
        self.g = load_ontology(ontology)
        self._expand()

        self.background_g = load_background_onts()
        self.background_onts_titles = load_background_onts_titles()
        self.props_labeled = label_props(self.background_g)

        self.toc: Dict[str, str] = {}
        self.fids: Dict[str, str] = {}
        self.ns = get_ns(self.g)

        # make HTML doc with title
        t = None
        for o in chain(
            self.g.subjects(RDF.type, OWL.Ontology),
            self.g.subjects(RDF.type, PROF.Profile),
            self.g.subjects(RDF.type, SKOS.ConceptScheme)
        ):
            for o2 in self.g.objects(o, DCTERMS.title):
                t = str(o2)
        self.doc = dominate.document(title=t)

        with self.doc:
            self.content = div(id="content")

    def _expand(self):
        # class types
        for s_ in self.g.subjects(RDF.type, OWL.Class):
            self.g.add((s_, RDF.type, RDFS.Class))

        # property types
        for s_ in chain(
            self.g.subjects(RDF.type, OWL.ObjectProperty),
            self.g.subjects(RDF.type, OWL.FunctionalProperty),
            self.g.subjects(RDF.type, OWL.DatatypeProperty),
            self.g.subjects(RDF.type, OWL.AnnotationProperty),
        ):
            self.g.add((s_, RDF.type, RDF.Property))

        # name
        for s_, o in chain(
            self.g.subject_objects(DC.title),
            self.g.subject_objects(RDFS.label),
            self.g.subject_objects(SKOS.prefLabel),
            self.g.subject_objects(SDO.name),
        ):
            self.g.add((s_, DCTERMS.title, o))

        # description
        for s_, o in chain(
            self.g.subject_objects(DC.description),
            self.g.subject_objects(RDFS.comment),
            self.g.subject_objects(SKOS.definition),
            self.g.subject_objects(SDO.description),
        ):
            self.g.add((s_, DCTERMS.description, o))

        # source
        for s_, o in self.g.subject_objects(DC.source):
            self.g.add((s_, DCTERMS.source, o))

        # owl:Restrictions from Blank Nodes
        for s_ in self.g.subjects(OWL.onProperty):
            self.g.add((s_, RDF.type, OWL.Restriction))

        # we do these next few so we only need to loop through Class & Property properties once: single subject
        for s_, o in self.g.subject_objects(RDFS.subClassOf):
            self.g.add((o, ONTDOC.superClassOf, s_))

        for s_, o in self.g.subject_objects(RDFS.subPropertyOf):
            self.g.add((o, ONTDOC.superPropertyOf, s_))

        for s_, o in self.g.subject_objects(RDFS.domain):
            self.g.add((o, ONTDOC.inDomainOf, s_))

        for s_, o in self.g.subject_objects(SDO.domainIncludes):
            self.g.add((o, ONTDOC.inDomainIncludesOf, s_))

        for s_, o in self.g.subject_objects(RDFS.range):
            self.g.add((o, ONTDOC.inRangeOf, s_))

        for s_, o in self.g.subject_objects(SDO.rangeIncludes):
            self.g.add((o, ONTDOC.inRangeIncludesOf, s_))

        for s_, o in self.g.subject_objects(RDF.type):
            self.g.add((o, ONTDOC.hasMember, s_))

        # Agents
        # creator
        for s_, o in chain(
            self.g.subject_objects(DC.creator),
            self.g.subject_objects(SDO.creator),
            self.g.subject_objects(
                SDO.author
            ),  # conflate SDO.author with DCTERMS.creator
        ):
            self.g.remove((s_, DC.creator, o))
            self.g.remove((s_, SDO.creator, o))
            self.g.remove((s_, SDO.author, o))
            self.g.add((s_, DCTERMS.creator, o))

        # contributor
        for s_, o in chain(
            self.g.subject_objects(DC.contributor),
            self.g.subject_objects(SDO.contributor),
        ):
            self.g.remove((s_, DC.contributor, o))
            self.g.remove((s_, SDO.contributor, o))
            self.g.add((s_, DCTERMS.contributor, o))

        # publisher
        for s_, o in chain(
            self.g.subject_objects(DC.publisher),
            self.g.subject_objects(SDO.publisher)
        ):
            self.g.remove((s_, DC.publisher, o))
            self.g.remove((s_, SDO.publisher, o))
            self.g.add((s_, DCTERMS.publisher, o))

        # indicate Agent instances from properties
        for o in chain(
            self.g.objects(None, DCTERMS.publisher),
            self.g.objects(None, DCTERMS.creator),
            self.g.objects(None, DCTERMS.contributor)
        ):
            self.g.add((o, RDF.type, PROV.Agent))

        # Agent annotations
        for s_, o in self.g.subject_objects(FOAF.name):
            self.g.add((s_, SDO.name, o))

        for s_, o in self.g.subject_objects(FOAF.mbox):
            self.g.add((s_, SDO.email, o))

        for s_, o in self.g.subject_objects(ORG.memberOf):
            self.g.add((s_, SDO.affiliation, o))

    def _make_document(self, schema_org_json):
        self._make_header(schema_org_json)
        self._make_body()

    def _make_header(self, schema_org_json):
        # use standard pyLODE stylesheet
        css = "\n" + open("pylode.css").read() + "\n\t"
        with self.doc.head:
            style(raw(css))
            link(
                rel="icon",
                type="image/png",
                sizes="16x16",
                href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhklEQVQ4jbWPzStEURjG3yQLirlGKUnKFO45Z+SjmXvnnmthQcpCoVhYmD/AwmJiI3OvZuZc2U3UlKU0/gAslMw9JgvhHxAr2fko7r0jHSsl+TgbTz2Lt5731/MASEiJW9ONml2QyX6rsGalmnT74v8BDf12hxJfpV8d1uwNKUBYszabdFv84L8B9X0rESVmmUup2fme0cVhJWaZHw4NWL1SewEAfDe6H3Dy6Ll456WEJsRZS630MwCAOI20ei5OBpxse5zcBZw8eS4uPpfIuDiCainIg9umBCU0GZzgLZ9Hn31OgoATL+CkLDGB5H1OKj4nFd/FBxUXJ0UZNb4edw/6nLyJXaj5FeCVyPLNIVmYK8TG1IwWb16L1gEACAFV90ftoT8bdOX0EeyY99gxBXZMgRz6qGb1KantAACI0UvE6F5XJqEjpsdURouI0Vt5gGOUkUNnPu7ObGIIMfNaGqDmjDRi9FZldF1lRgYzeqUyeoiY4ag5Iy3RgOYRM8+/M2bG8efsO4hGrpmJseyMAAAAAElFTkSuQmCC",
            )
            link(
                rel="icon",
                type="image/png",
                sizes="32x32",
                href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAC40lEQVRYhe2UT0hUQRzHp6Iss1B3VZKIDbbdfW9mnoi4f3zzjkJQeOgS0SEIb1EWBGGlLLu460zQPQM1unUIIjA6rfpm6ZAhHjoIRVQUFUlEbG+euTsdXG1d3VL3bVD4g+9h+L35fT/8fvN7ADgY9aHY5fpIvK82HO9ysu66wxWOzbkjcekKx0a2ALYA/n2AGi3a6ArFezcidziecQygNhhrcUficjP6PwBqtGijKxy/thnVBePHywYoDsFhl53GV8SEcsTx4usCMLUewTVpc23BNvEzm6Neyf1+KcG2vwqwUjgrOJq2JmHftwmkVBRGTvncFodnbI7vChO/FRznCmHsNM7aHM9Yk7Df5iqsLMw9sMNOK2g+jS4IEz0UJv4iuJZb2RltWnB4UZqH6ioGAgAAGe5vtiZhtzDx7OoRadLmeM7m6IRjhnLMW2Vx1bA5GhAmnhIcz6/xNj4Ujsky8UspwfayjDPjsF2Y6L7N8Vzx/BfP+KPg6LbgSqd8DnfJW2CnbaLhfH5ephpqygJYvQU4Z3P82TLRsDDhUTnmrSq+Y3N0Mg+Xldy/zwEAnLMWZ3pHpNExmfLs/t0dOdVcbT0JeKxUwFP2VljjqiE47Jp53LTXNxhsUZjerTByXWX6VZWRs/4bIQ2ACv+UAomgDzLCISNZxAxZKMhIDjLy1JfsaK+I+eGBUBNk5E2x8RogX/PdcDZUqieWTSh5D6nOVKqfhoycUmlHFFIyu5RXqf7AcQDISCpv/tqbMBqK883RtmpISRoxQyJKPgGn3wNk5NEigDFa6hslqV/Kj+FdBQD0bshIDlKSLlVcoWQo36UhR80BAMB73lulMn0EMpJTqD6qJiOt3mho/8GbkT2BZNgDB/V+RI0fkOrT3kRIVQbaDizJm2hdNbINBxwk5xAj3yEjuV9rZ1iIkgxixkLBA83mz8uCjLwoGwAx0vOnFSy5mtR4VTaAQvVORMnwZgSpzkrV/QmdE2tKe46+MQAAAABJRU5ErkJggg==",
            )
            meta(http_equiv="Content-Type", content="text/html; charset=utf-8")
            script(raw("\n" + schema_org_json + "\n\t"), type="application/ld+json")

    def _make_body(self):
        self._make_pylode_logo()
        self._make_metadata()
        self._make_all_elements()
        self._make_namespaces()
        self._make_legend()
        self._make_toc()

    def _make_pylode_logo(self):
        from pylode3.pylode3 import __version__ as v
        with self.doc:
            with div(id="pylode"):
                with p("made by "):
                    with a(href="https://github.com/rdflib/pyLODE"):
                        span("p", id="p")
                        span("y", id="y")
                        span("LODE")
                    a(
                        version,
                        href="https://github.com/rdflib/pyLODE/release/" + v,
                        id="version",
                    )

    def _make_metadata(self):
        # get all ONT_PROPS props and their (multiple) values
        this_onts_props = defaultdict(list)
        for s_ in chain(
                self.g.subjects(predicate=RDF.type, object=OWL.Ontology),
                self.g.subjects(predicate=RDF.type, object=SKOS.ConceptScheme),
                self.g.subjects(predicate=RDF.type, object=PROF.Profile),
        ):
            iri = s_
            for p_, o in self.g.predicate_objects(s_):
                if p_ in ONT_PROPS:
                    this_onts_props[p_].append(o)

        # make HTML for all props in order of ONT_PROPS
        sec = div(h1(this_onts_props[DCTERMS.title]), id="metadata", _class="section")
        d = dl(div(dt(strong("IRI")), dd(code(str(iri)))))
        for prop in ONT_PROPS:
            if prop in this_onts_props.keys():
                d.appendChild(
                    prop_obj_pair_html(
                        self.g,
                        self.background_g,
                        self.ns,
                        "dl",
                        prop,
                        self.props_labeled[prop]["title"],
                        self.props_labeled[prop]["description"],
                        self.props_labeled[prop]["ont_title"],
                        self.fids,
                        this_onts_props[prop],
                    )
                )
        sec.appendChild(d)
        self.content.appendChild(sec)

    def _make_all_elements(self):
        with self.content:
            if (None, RDF.type, OWL.Class) in self.g:
                with div(id="classes", _class="section"):
                    h2("Classes")
                    elements_html(self.g, self.background_g, self.ns, OWL.Class, CLASS_PROPS, self.toc, "classes", self.fids, self.props_labeled)

            if (None, RDF.type, RDF.Property) in self.g:
                with div(id="properties", _class="section"):
                    h2("Properties")
                    elements_html(self.g, self.background_g, self.ns, RDF.Property, PROP_PROPS, self.toc, "properties", self.fids, self.props_labeled)

                    if (None, RDF.type, OWL.ObjectProperty) in self.g:
                        with div(id="objectproperties", _class="section"):
                            h3("Object Properties")
                            elements_html(self.g, self.background_g, self.ns, OWL.ObjectProperty, PROP_PROPS, self.toc, "objectproperties", self.fids, self.props_labeled)

                    if (None, RDF.type, OWL.DatatypeProperty) in self.g:
                        with div(id="datatypeproperties", _class="section"):
                            h3("Datatype Properties")
                            elements_html(self.g, self.background_g, self.ns, OWL.DatatypeProperty, PROP_PROPS, self.toc, "datatypeproperties", self.fids, self.props_labeled)

                    if (None, RDF.type, OWL.AnnotationProperty) in self.g:
                        with div(id="annotationproperties", _class="section"):
                            h3("Annotation Properties")
                            elements_html(self.g, self.background_g, self.ns, OWL.AnnotationProperty, PROP_PROPS, self.toc, "annotationproperties", self.fids, self.props_labeled)

                    if (None, RDF.type, OWL.FunctionalProperty) in self.g:
                        with div(id="functionalproperties", _class="section"):
                            h3("Functional Properties")
                            elements_html(self.g, self.background_g, self.ns, OWL.FunctionalProperty, PROP_PROPS, self.toc, "functionalproperties", self.fids, self.props_labeled)

    def _make_legend(self):
        with self.content:
            with div(id="legend"):
                h2("Legend")
                with table(_class="entity"):

                    if self.toc.get("classes") is not None:
                        with tr():
                            td(sup("c", _class="sup-c", title="OWL/RDFS Class"))
                            td("Classes")
                    if self.toc.get("properties") is not None:
                        with tr():
                            td(sup("p", _class="sup-p", title="RDF Property"))
                            td("Properties")
                    if self.toc.get("objectproperties") is not None:
                        with tr():
                            td(
                                sup(
                                    "op", _class="sup-op", title="OWL Object Property"
                                )
                            )
                            td("Object Properties")
                    if self.toc.get("datatypeproperties") is not None:
                        with tr():
                            td(
                                sup(
                                    "dp",
                                    _class="sup-dp",
                                    title="OWL Datatype Property",
                                )
                            )
                            td("Datatype Properties")
                    if self.toc.get("annotationproperties") is not None:
                        with tr():
                            td(
                                sup(
                                    "ap",
                                    _class="sup-ap",
                                    title="OWL Annotation Property",
                                )
                            )
                            td("Annotation Properties")
                    if self.toc.get("functionalproperties") is not None:
                        with tr():
                            td(
                                sup(
                                    "fp",
                                    _class="sup-fp",
                                    title="OWL Functional Property",
                                )
                            )
                            td("Functional Properties")
                    if self.toc.get("named_individuals") is not None:
                        with tr():
                            td(sup("ni", _class="sup-ni", title="OWL Named Individual"))
                            td("Named Individuals")

    def _make_namespaces(self):
        # get only namespaces used in ont
        nses = {}
        for n in chain(self.g.subjects(), self.g.predicates(), self.g.objects()):
            for prefix, ns in self.g.namespaces():
                if str(n).startswith(ns):
                    nses[prefix] = ns

        with self.content:
            with div(id="namespaces"):
                h2("Namespaces")
                with dl():
                    if self.toc.get("namespaces") is None:
                        self.toc["namespaces"] = []
                    for prefix, ns in sorted(nses.items()):
                        p_ = prefix if prefix != "" else ":"
                        dt(p_, id=p_)
                        dd(code(ns))
                        self.toc["namespaces"].append(("#" + prefix, prefix))

    def _make_toc(self):
        with self.doc:
            with div(id="toc"):
                h3("Table of Contents")
                with ul(_class="first"):
                    li(h4(a("Metadata", href="#metadata")))

                    if self.toc.get("classes") is not None and len(self.toc["classes"]) > 0:
                        with li():
                            h4(a("Classes", href="#classes"))
                            with ul(_class="second"):
                                for c in self.toc["classes"]:
                                    li(a(c[1], href=c[0]))

                    if self.toc.get("properties") is not None and len(self.toc["properties"]) > 0:
                        with li():
                            h4(a("Properties", href="#properties"))
                            with ul(_class="second"):
                                for c in self.toc["properties"]:
                                    li(a(c[1], href=c[0]))

                    if self.toc.get("objectproperties") is not None and len(self.toc["objectproperties"]) > 0:
                        with li():
                            h4(a("Object Properties", href="#objectproperties"))
                            with ul(_class="second"):
                                for c in self.toc["objectproperties"]:
                                    li(a(c[1], href=c[0]))

                    if self.toc.get("datatypeproperties") is not None and len(self.toc["datatypeproperties"]) > 0:
                        with li():
                            h4(a("Datatype Properties", href="#datatypeproperties"))
                            with ul(_class="second"):
                                for c in self.toc["datatypeproperties"]:
                                    li(a(c[1], href=c[0]))

                    if self.toc.get("annotationproperties") is not None and len(self.toc["annotationproperties"]) > 0:
                        with li():
                            h4(a("Annotation Properties", href="#annotationproperties"))
                            with ul(_class="second"):
                                for c in self.toc["annotationproperties"]:
                                    li(a(c[1], href=c[0]))

                    if self.toc.get("functionalproperties") is not None and len(self.toc["functionalproperties"]) > 0:
                        with li():
                            h4(a("Functional Properties", href="#functionalproperties"))
                            with ul(_class="second"):
                                for c in self.toc["functionalproperties"]:
                                    li(a(c[1], href=c[0]))

                    with li():
                        h4(a("Namespaces", href="#namespaces"))
                        with ul(_class="second"):
                            for n in self.toc["namespaces"]:
                                li(a(n[1], href="#" + n[1]))

                    li(h4(a("Legend", href="#legend")), ul(_class="second"))


if __name__ == "__main__":
    # TODO: schema.org generation from ont
    # TODO: add title of ont to head
    # TODO: cli UI

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    sdo_json = """[
      {
        "@id": "https://example.com",
        "@type": [
          "https://schema.org/DefinedTermSet"
        ],
        "https://schema.org/description": [
          {
            "@value": "<p>This ontology contains several simple classes and properties about animals that are defined only to show off pyLODE's ability to represent different forms of example rendering.</p>"
          }
        ],
        "https://schema.org/license": [
          {
            "@id": "https://creativecommons.org/licenses/by/4.0/"
          }
        ],
        "https://schema.org/name": [
          {
            "@value": "Examples Ontology"
          }
        ],
        "https://schema.org/rights": [
          {
            "@value": "&copy; SURROUND Australia Pty Ltd"
          }
        ]
      }
    ]"""
    version = "3.0.0"

    od = OntDoc(ontology="agrif.ttl")
    od._make_document(sdo_json)
    open("some.html", "w").write(od.doc.render())

    # import cProfile
    #
    # pr = cProfile.Profile()
    # pr.enable()
    #
    # check_all_props_are_known()
    #
    # pr.disable()
    # pr.print_stats(sort='time')
