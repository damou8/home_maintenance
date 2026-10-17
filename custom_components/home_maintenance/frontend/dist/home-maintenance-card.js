var Nt=Object.defineProperty;var Ot=Object.getOwnPropertyDescriptor;var E=(r,t,e,i)=>{for(var n=i>1?void 0:i?Ot(t,e):t,a=r.length-1,o;a>=0;a--)(o=r[a])&&(n=(i?o(t,e,n):o(n))||n);return i&&n&&Nt(t,e,n),n};var q=globalThis,z=q.ShadowRoot&&(q.ShadyCSS===void 0||q.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,G=Symbol(),ct=new WeakMap,O=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==G)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(z&&t===void 0){let i=e!==void 0&&e.length===1;i&&(t=ct.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&ct.set(e,t))}return t}toString(){return this.cssText}},lt=r=>new O(typeof r=="string"?r:r+"",void 0,G),J=(r,...t)=>{let e=r.length===1?r[0]:t.reduce((i,n,a)=>i+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+r[a+1],r[0]);return new O(e,r,G)},ut=(r,t)=>{if(z)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let i=document.createElement("style"),n=q.litNonce;n!==void 0&&i.setAttribute("nonce",n),i.textContent=e.cssText,r.appendChild(i)}},Z=z?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(let i of t.cssRules)e+=i.cssText;return lt(e)})(r):r;var{is:It,defineProperty:Mt,getOwnPropertyDescriptor:Pt,getOwnPropertyNames:Rt,getOwnPropertySymbols:Ut,getPrototypeOf:Ht}=Object,y=globalThis,dt=y.trustedTypes,Ft=dt?dt.emptyScript:"",Lt=y.reactiveElementPolyfillSupport,I=(r,t)=>r,M={toAttribute(r,t){switch(t){case Boolean:r=r?Ft:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},W=(r,t)=>!It(r,t),mt={attribute:!0,type:String,converter:M,reflect:!1,useDefault:!1,hasChanged:W};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),y.litPropertyMetadata??(y.litPropertyMetadata=new WeakMap);var g=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=mt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let i=Symbol(),n=this.getPropertyDescriptor(t,i,e);n!==void 0&&Mt(this.prototype,t,n)}}static getPropertyDescriptor(t,e,i){let{get:n,set:a}=Pt(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:n,set(o){let c=n?.call(this);a?.call(this,o),this.requestUpdate(t,c,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??mt}static _$Ei(){if(this.hasOwnProperty(I("elementProperties")))return;let t=Ht(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(I("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(I("properties"))){let e=this.properties,i=[...Rt(e),...Ut(e)];for(let n of i)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[i,n]of e)this.elementProperties.set(i,n)}this._$Eh=new Map;for(let[e,i]of this.elementProperties){let n=this._$Eu(e,i);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let i=new Set(t.flat(1/0).reverse());for(let n of i)e.unshift(Z(n))}else t!==void 0&&e.push(Z(t));return e}static _$Eu(t,e){let i=e.attribute;return i===!1?void 0:typeof i=="string"?i:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ut(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){let i=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,i);if(n!==void 0&&i.reflect===!0){let a=(i.converter?.toAttribute!==void 0?i.converter:M).toAttribute(e,i.type);this._$Em=t,a==null?this.removeAttribute(n):this.setAttribute(n,a),this._$Em=null}}_$AK(t,e){let i=this.constructor,n=i._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let a=i.getPropertyOptions(n),o=typeof a.converter=="function"?{fromAttribute:a.converter}:a.converter?.fromAttribute!==void 0?a.converter:M;this._$Em=n;let c=o.fromAttribute(e,a.type);this[n]=c??this._$Ej?.get(n)??c,this._$Em=null}}requestUpdate(t,e,i,n=!1,a){if(t!==void 0){let o=this.constructor;if(n===!1&&(a=this[t]),i??(i=o.getPropertyOptions(t)),!((i.hasChanged??W)(a,e)||i.useDefault&&i.reflect&&a===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,i))))return;this.C(t,e,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:n,wrapped:a},o){i&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,o??e??this[t]),a!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(let[n,a]of this._$Ep)this[n]=a;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[n,a]of i){let{wrapped:o}=a,c=this[n];o!==!0||this._$AL.has(n)||c===void 0||this.C(n,void 0,a,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(e)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(e=>this._$ET(e,this[e]))),this._$EM()}updated(t){}firstUpdated(t){}};g.elementStyles=[],g.shadowRootOptions={mode:"open"},g[I("elementProperties")]=new Map,g[I("finalized")]=new Map,Lt?.({ReactiveElement:g}),(y.reactiveElementVersions??(y.reactiveElementVersions=[])).push("2.1.2");var R=globalThis,ht=r=>r,B=R.trustedTypes,pt=B?B.createPolicy("lit-html",{createHTML:r=>r}):void 0,bt="$lit$",v=`lit$${Math.random().toFixed(9).slice(2)}$`,wt="?"+v,jt=`<${wt}>`,x=document,U=()=>x.createComment(""),H=r=>r===null||typeof r!="object"&&typeof r!="function",rt=Array.isArray,qt=r=>rt(r)||typeof r?.[Symbol.iterator]=="function",Q=`[ 	
\f\r]`,P=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ft=/-->/g,gt=/>/g,$=RegExp(`>|${Q}(?:([^\\s"'>=/]+)(${Q}*=${Q}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),_t=/'/g,yt=/"/g,$t=/^(?:script|style|textarea|title)$/i,at=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),b=at(1),ne=at(2),re=at(3),S=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),vt=new WeakMap,A=x.createTreeWalker(x,129);function At(r,t){if(!rt(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return pt!==void 0?pt.createHTML(t):t}var zt=(r,t)=>{let e=r.length-1,i=[],n,a=t===2?"<svg>":t===3?"<math>":"",o=P;for(let c=0;c<e;c++){let s=r[c],u,m,l=-1,h=0;for(;h<s.length&&(o.lastIndex=h,m=o.exec(s),m!==null);)h=o.lastIndex,o===P?m[1]==="!--"?o=ft:m[1]!==void 0?o=gt:m[2]!==void 0?($t.test(m[2])&&(n=RegExp("</"+m[2],"g")),o=$):m[3]!==void 0&&(o=$):o===$?m[0]===">"?(o=n??P,l=-1):m[1]===void 0?l=-2:(l=o.lastIndex-m[2].length,u=m[1],o=m[3]===void 0?$:m[3]==='"'?yt:_t):o===yt||o===_t?o=$:o===ft||o===gt?o=P:(o=$,n=void 0);let p=o===$&&r[c+1].startsWith("/>")?" ":"";a+=o===P?s+jt:l>=0?(i.push(u),s.slice(0,l)+bt+s.slice(l)+v+p):s+v+(l===-2?c:p)}return[At(r,a+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),i]},F=class r{constructor({strings:t,_$litType$:e},i){let n;this.parts=[];let a=0,o=0,c=t.length-1,s=this.parts,[u,m]=zt(t,e);if(this.el=r.createElement(u,i),A.currentNode=this.el.content,e===2||e===3){let l=this.el.content.firstChild;l.replaceWith(...l.childNodes)}for(;(n=A.nextNode())!==null&&s.length<c;){if(n.nodeType===1){if(n.hasAttributes())for(let l of n.getAttributeNames())if(l.endsWith(bt)){let h=m[o++],p=n.getAttribute(l).split(v),w=/([.?@])?(.*)/.exec(h);s.push({type:1,index:a,name:w[2],strings:p,ctor:w[1]==="."?tt:w[1]==="?"?et:w[1]==="@"?it:T}),n.removeAttribute(l)}else l.startsWith(v)&&(s.push({type:6,index:a}),n.removeAttribute(l));if($t.test(n.tagName)){let l=n.textContent.split(v),h=l.length-1;if(h>0){n.textContent=B?B.emptyScript:"";for(let p=0;p<h;p++)n.append(l[p],U()),A.nextNode(),s.push({type:2,index:++a});n.append(l[h],U())}}}else if(n.nodeType===8)if(n.data===wt)s.push({type:2,index:a});else{let l=-1;for(;(l=n.data.indexOf(v,l+1))!==-1;)s.push({type:7,index:a}),l+=v.length-1}a++}}static createElement(t,e){let i=x.createElement("template");return i.innerHTML=t,i}};function k(r,t,e=r,i){if(t===S)return t;let n=i!==void 0?e._$Co?.[i]:e._$Cl,a=H(t)?void 0:t._$litDirective$;return n?.constructor!==a&&(n?._$AO?.(!1),a===void 0?n=void 0:(n=new a(r),n._$AT(r,e,i)),i!==void 0?(e._$Co??(e._$Co=[]))[i]=n:e._$Cl=n),n!==void 0&&(t=k(r,n._$AS(r,t.values),n,i)),t}var X=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:i}=this._$AD,n=(t?.creationScope??x).importNode(e,!0);A.currentNode=n;let a=A.nextNode(),o=0,c=0,s=i[0];for(;s!==void 0;){if(o===s.index){let u;s.type===2?u=new L(a,a.nextSibling,this,t):s.type===1?u=new s.ctor(a,s.name,s.strings,this,t):s.type===6&&(u=new nt(a,this,t)),this._$AV.push(u),s=i[++c]}o!==s?.index&&(a=A.nextNode(),o++)}return A.currentNode=x,n}p(t){let e=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}},L=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,n){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=k(this,t,e),H(t)?t===d||t==null||t===""?(this._$AH!==d&&this._$AR(),this._$AH=d):t!==this._$AH&&t!==S&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):qt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==d&&H(this._$AH)?this._$AA.nextSibling.data=t:this.T(x.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:i}=t,n=typeof i=="number"?this._$AC(t):(i.el===void 0&&(i.el=F.createElement(At(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(e);else{let a=new X(n,this),o=a.u(this.options);a.p(e),this.T(o),this._$AH=a}}_$AC(t){let e=vt.get(t.strings);return e===void 0&&vt.set(t.strings,e=new F(t)),e}k(t){rt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,i,n=0;for(let a of t)n===e.length?e.push(i=new r(this.O(U()),this.O(U()),this,this.options)):i=e[n],i._$AI(a),n++;n<e.length&&(this._$AR(i&&i._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let i=ht(t).nextSibling;ht(t).remove(),t=i}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,n,a){this.type=1,this._$AH=d,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=a,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=d}_$AI(t,e=this,i,n){let a=this.strings,o=!1;if(a===void 0)t=k(this,t,e,0),o=!H(t)||t!==this._$AH&&t!==S,o&&(this._$AH=t);else{let c=t,s,u;for(t=a[0],s=0;s<a.length-1;s++)u=k(this,c[i+s],e,s),u===S&&(u=this._$AH[s]),o||(o=!H(u)||u!==this._$AH[s]),u===d?t=d:t!==d&&(t+=(u??"")+a[s+1]),this._$AH[s]=u}o&&!n&&this.j(t)}j(t){t===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},tt=class extends T{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===d?void 0:t}},et=class extends T{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==d)}},it=class extends T{constructor(t,e,i,n,a){super(t,e,i,n,a),this.type=5}_$AI(t,e=this){if((t=k(this,t,e,0)??d)===S)return;let i=this._$AH,n=t===d&&i!==d||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,a=t!==d&&(i===d||n);n&&this.element.removeEventListener(this.name,this,i),a&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},nt=class{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){k(this,t)}};var Wt=R.litHtmlPolyfillSupport;Wt?.(F,L),(R.litHtmlVersions??(R.litHtmlVersions=[])).push("3.3.3");var xt=(r,t,e)=>{let i=e?.renderBefore??t,n=i._$litPart$;if(n===void 0){let a=e?.renderBefore??null;i._$litPart$=n=new L(t.insertBefore(U(),a),a,void 0,e??{})}return n._$AI(r),n};var j=globalThis,f=class extends g{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var e;let t=super.createRenderRoot();return(e=this.renderOptions).renderBefore??(e.renderBefore=t.firstChild),t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=xt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return S}};f._$litElement$=!0,f.finalized=!0,j.litElementHydrateSupport?.({LitElement:f});var Bt=j.litElementPolyfillSupport;Bt?.({LitElement:f});(j.litElementVersions??(j.litElementVersions=[])).push("4.2.2");var Vt={attribute:!0,type:String,converter:M,reflect:!1,hasChanged:W},Kt=(r=Vt,t,e)=>{let{kind:i,metadata:n}=e,a=globalThis.litPropertyMetadata.get(n);if(a===void 0&&globalThis.litPropertyMetadata.set(n,a=new Map),i==="setter"&&((r=Object.create(r)).wrapped=!0),a.set(e.name,r),i==="accessor"){let{name:o}=e;return{set(c){let s=t.get.call(this);t.set.call(this,c),this.requestUpdate(o,s,r,!0,c)},init(c){return c!==void 0&&this.C(o,void 0,r,c),c}}}if(i==="setter"){let{name:o}=e;return function(c){let s=this[o];t.call(this,c),this.requestUpdate(o,s,r,!0,c)}}throw Error("Unsupported decorator location: "+i)};function C(r){return(t,e)=>typeof e=="object"?Kt(r,t,e):((i,n,a)=>{let o=n.hasOwnProperty(a);return n.constructor.createProperty(a,i),o?Object.getOwnPropertyDescriptor(n,a):void 0})(r,t,e)}function V(r){return C({...r,state:!0,attribute:!1})}var St,Et;var kt=function(r,t){return Yt(t).format(r)},Yt=function(r){return new Intl.DateTimeFormat(r.language,{year:"numeric",month:"numeric",day:"numeric"})};(function(r){r.language="language",r.system="system",r.comma_decimal="comma_decimal",r.decimal_comma="decimal_comma",r.space_comma="space_comma",r.none="none"})(St||(St={})),(function(r){r.language="language",r.system="system",r.am_pm="12",r.twenty_four="24"})(Et||(Et={}));var Tt={en:{next:"Next: {date} ({pct}%)",unknown:"Unknown",confirm_complete:"Do you really want to mark this task as done?",no_tasks:"No tasks",card_name:"Home Maintenance",card_description:"Your maintenance tasks, colored by how soon they are due.",title:"Title",show_disabled:"Show disabled tasks",labels:"Only tasks with these labels",warning_threshold:"Blue below (% of interval left)",tap_action:"Tap action",hold_action:"Hold action"},fr:{next:"Prochain : {date} ({pct}%)",unknown:"Inconnue",confirm_complete:"Voulez-vous vraiment marquer cette t\xE2che comme effectu\xE9e ?",no_tasks:"Aucune t\xE2che",card_name:"Home Maintenance",card_description:"Vos t\xE2ches de maintenance, color\xE9es selon leur \xE9ch\xE9ance.",title:"Titre",show_disabled:"Afficher les t\xE2ches d\xE9sactiv\xE9es",labels:"Uniquement les t\xE2ches avec ces \xE9tiquettes",warning_threshold:"Bleu en dessous de (% d'intervalle restant)",tap_action:"Action au toucher",hold_action:"Action en maintenant"},de:{next:"N\xE4chste: {date} ({pct} %)",unknown:"Unbekannt",confirm_complete:"M\xF6chtest du diese Aufgabe wirklich als erledigt markieren?",no_tasks:"Keine Aufgaben",card_name:"Home Maintenance",card_description:"Deine Wartungsaufgaben, eingef\xE4rbt nach F\xE4lligkeit.",title:"Titel",show_disabled:"Deaktivierte Aufgaben anzeigen",labels:"Nur Aufgaben mit diesen Labels",warning_threshold:"Blau unter (% verbleibendes Intervall)",tap_action:"Aktion beim Tippen",hold_action:"Aktion beim Halten"}};function _(r,t,e={}){let i=(r??"en").split("-")[0];return(Tt[i]?.[t]??Tt.en[t]??t).replace(/\{(\w+)\}/g,(a,o)=>String(e[o]??""))}var Gt=[{name:"title",selector:{text:{}}},{name:"show_disabled",selector:{boolean:{}}},{name:"labels",selector:{label:{multiple:!0}}},{name:"warning_threshold",selector:{number:{min:0,max:100,mode:"box",unit_of_measurement:"%"}}},{name:"tap_action",selector:{ui_action:{}}},{name:"hold_action",selector:{ui_action:{}}}],D=class extends f{setConfig(t){this._config=t}render(){return!this.hass||!this._config?d:b`
            <ha-form
                .hass=${this.hass}
                .data=${this._config}
                .schema=${Gt}
                .computeLabel=${t=>_(this.hass.language,t.name)}
                @value-changed=${this._valueChanged}
            ></ha-form>
        `}_valueChanged(t){let e={...t.detail.value};for(let i of Object.keys(e))(e[i]===""||e[i]===void 0||Array.isArray(e[i])&&!e[i].length)&&delete e[i];this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:e},bubbles:!0,composed:!0}))}};E([C({attribute:!1})],D.prototype,"hass",2),E([V()],D.prototype,"_config",2);var Jt=15,Zt=500,Y={due:"var(--red-color, #f44336)",soon:"var(--blue-color, #2196f3)",ok:"var(--green-color, #4caf50)",disabled:"var(--disabled-color, #bdbdbd)"},N=class extends f{constructor(){super(...arguments);this._held=!1}static getConfigElement(){return document.createElement("home-maintenance-card-editor")}static getStubConfig(){return{}}setConfig(e){if(!e)throw new Error("Invalid configuration");this._config=e}getCardSize(){return Math.max(1,this._tasks().length)}getGridOptions(){return{columns:"full",min_columns:6}}_tasks(){if(!this.hass||!this._config)return[];let e=this.hass,i=this._config.labels??[],n=this._config.show_disabled??!1,a=Date.now(),o=[];for(let c of Object.values(e.entities??{})){if(c.platform!=="home_maintenance"||!c.entity_id.startsWith("binary_sensor.")||c.hidden||i.length&&!(c.labels??[]).some(Dt=>i.includes(Dt)))continue;let s=e.states[c.entity_id];if(!s)continue;let u=s.attributes,m=u.enabled!==!1;if(!m&&!n)continue;let l=Date.parse(u.last_performed),h=Date.parse(u.next_due),p=100;!isNaN(l)&&!isNaN(h)&&h>l&&(p=Math.min(100,Math.max(0,Math.trunc((h-a)/(h-l)*100))));let[w,ot,st]=String(u.next_due??"").slice(0,10).split("-").map(Number),Ct=w&&ot&&st?new Date(w,ot-1,st):void 0;o.push({entity_id:c.entity_id,name:this._taskName(c,s),icon:u.icon??"mdi:calendar-check",due:s.state==="on",enabled:m,next:Ct,pct:p})}return o.sort((c,s)=>Number(s.enabled)-Number(c.enabled)||Number(s.due)-Number(c.due)||(c.next?.getTime()??1/0)-(s.next?.getTime()??1/0)||c.name.localeCompare(s.name))}_taskName(e,i){let n=i.attributes.friendly_name??e.entity_id,a=this.hass.devices?.[e.device_id],o=a?.name_by_user??a?.name;return o&&n.startsWith(`${o} `)?n.slice(o.length+1):n}_color(e){return e.enabled?e.due?Y.due:e.pct<=(this._config?.warning_threshold??Jt)?Y.soon:Y.ok:Y.disabled}_actionConfig(e){let i=this.hass?.language,n=this._config?.tap_action??{action:"perform-action",perform_action:"home_maintenance.reset_last_performed",confirmation:{text:_(i,"confirm_complete")}};return{entity:e.entity_id,tap_action:this._withTarget(n,e.entity_id),hold_action:this._withTarget(this._config?.hold_action??{action:"more-info"},e.entity_id)}}_withTarget(e,i){return!["perform-action","call-service"].includes(e.action)||e.target||e.data?.entity_id||e.service_data?.entity_id?e:{...e,target:{entity_id:i}}}_fireAction(e,i){this.dispatchEvent(new CustomEvent("hass-action",{detail:{config:this._actionConfig(e),action:i},bubbles:!0,composed:!0}))}_onPointerDown(e){this._held=!1,window.clearTimeout(this._holdTimer),this._holdTimer=window.setTimeout(()=>{this._held=!0,this._fireAction(e,"hold")},Zt)}_onPointerUp(){window.clearTimeout(this._holdTimer)}_onClick(e){if(this._held){this._held=!1;return}this._fireAction(e,"tap")}_onKeyDown(e,i){(e.key==="Enter"||e.key===" ")&&(e.preventDefault(),this._fireAction(i,"tap"))}render(){if(!this.hass||!this._config)return d;let e=this._tasks(),i=this.hass.language;return b`
            ${this._config.title?b`<div class="title">${this._config.title}</div>`:d}
            ${e.length===0?b`<ha-card class="empty">${_(i,"no_tasks")}</ha-card>`:b`
                    <div class="tasks">
                        ${e.map(n=>this._renderTask(n))}
                    </div>
                `}
        `}_renderTask(e){let i=this.hass.language,n=e.next?kt(e.next,this.hass.locale):_(i,"unknown");return b`
            <ha-card
                class="task ${e.enabled?"":"disabled"}"
                tabindex="0"
                role="button"
                @click=${()=>this._onClick(e)}
                @pointerdown=${()=>this._onPointerDown(e)}
                @pointerup=${this._onPointerUp}
                @pointerleave=${this._onPointerUp}
                @pointercancel=${this._onPointerUp}
                @contextmenu=${a=>a.preventDefault()}
                @keydown=${a=>this._onKeyDown(a,e)}
            >
                <div class="container">
                    <div class="icon ${e.due&&e.enabled?"pulse":""}" style="--icon-color: ${this._color(e)}">
                        <ha-icon .icon=${e.icon}></ha-icon>
                    </div>
                    <div class="info">
                        <span class="primary">${e.name}</span>
                        <span class="secondary">${_(i,"next",{date:n,pct:e.pct})}</span>
                    </div>
                </div>
            </ha-card>
        `}};N.styles=J`
        :host {
            display: block;
        }
        .title {
            font-size: var(--ha-card-header-font-size, 24px);
            font-weight: var(--ha-font-weight-normal, 400);
            color: var(--ha-card-header-color, var(--primary-text-color));
            padding: 4px 4px 8px;
        }
        .tasks {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(var(--home-maintenance-card-min-width, 300px), 1fr));
            gap: var(--grid-card-gap, 8px);
        }
        ha-card {
            cursor: pointer;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }
        ha-card:focus-visible {
            outline: 2px solid var(--primary-color);
            outline-offset: 2px;
        }
        ha-card.empty {
            padding: 12px;
            cursor: default;
            color: var(--secondary-text-color);
        }
        ha-card.disabled .info {
            opacity: 0.6;
        }
        .task {
            height: 56px;
            box-sizing: border-box;
        }
        .container {
            display: flex;
            align-items: center;
            gap: 10px;
            height: 100%;
            padding: 0 10px;
            box-sizing: border-box;
        }
        .icon {
            flex: none;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            margin: 6px 0;
            border-radius: 50%;
            color: var(--icon-color);
            --mdc-icon-size: 24px;
        }
        .icon.pulse {
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.6; }
            100% { transform: scale(1); opacity: 1; }
        }
        .info {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        .primary {
            font-size: 14px;
            font-weight: var(--ha-font-weight-medium, 500);
            line-height: 22.4px;
            letter-spacing: 0.1px;
            color: var(--primary-text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .secondary {
            font-size: 12px;
            font-weight: var(--ha-font-weight-normal, 400);
            line-height: 14.4px;
            letter-spacing: 0.4px;
            color: var(--primary-text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    `,E([C({attribute:!1})],N.prototype,"hass",2),E([V()],N.prototype,"_config",2);Promise.race([customElements.whenDefined("home-assistant"),customElements.whenDefined("hc-main")]).then(()=>{if(customElements.get("home-maintenance-card"))return;customElements.define("home-maintenance-card",N),customElements.define("home-maintenance-card-editor",D);let r=document.documentElement.lang;window.customCards=window.customCards||[],window.customCards.push({type:"home-maintenance-card",name:_(r,"card_name"),description:_(r,"card_description"),preview:!0})});
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
@lit/reactive-element/decorators/custom-element.js:
@lit/reactive-element/decorators/property.js:
@lit/reactive-element/decorators/state.js:
@lit/reactive-element/decorators/event-options.js:
@lit/reactive-element/decorators/base.js:
@lit/reactive-element/decorators/query.js:
@lit/reactive-element/decorators/query-all.js:
@lit/reactive-element/decorators/query-async.js:
@lit/reactive-element/decorators/query-assigned-nodes.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-assigned-elements.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
