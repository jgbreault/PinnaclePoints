class PageHeader extends HTMLElement {
   connectedCallback() {
      this.innerHTML = `
               <header id="header">
                  <div class="inner">

                     <!-- Logo -->
                        <a href="../../index.html" class="logo">
                           <span class="symbol"><img src="../../images/pinnacle_point_logo.png" alt="" /></span><span class="title">Pinnacle Points</span></br>
                           <span class="medium-font">Points where no higher</br>point can be seen</span>
                        </a>

                     <!-- Nav -->
                        <nav>
                           <ul>
                              <li><a href="#menu">Menu</a></li>
                           </ul>
                        </nav>

                  </div>
               </header>
      `;
   }
}


customElements.define("page-header", PageHeader);
