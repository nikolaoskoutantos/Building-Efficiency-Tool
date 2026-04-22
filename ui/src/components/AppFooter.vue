<template>
  <CFooter class="app-footer px-4 py-4">
    <div class="footer-content">
      <div class="footer-main">
        <div class="footer-logo-wrap">
          <img
            src="@/assets/images/EN-Funded-by-the-EU-NEG-1536x322.png"
            alt="Funded by the European Union"
            class="footer-logo footer-logo-eu"
          />
        </div>

        <div class="footer-logo-wrap footer-logo-wrap-right">
          <img
            src="@/assets/images/buildchain-300x103.png"
            alt="BUILDCHAIN"
            class="footer-logo footer-logo-buildchain"
          />
        </div>
      </div>

      <p class="footer-link-row">
        <a href="https://buildchain-project.eu/" target="_blank" rel="noopener noreferrer">
          Official Buildchain page
        </a>
      </p>

      <p class="footer-funding">
        BUILDCHAIN has received funding from the European Union’s Horizon Europe research and
        innovation programme under grant agreement no 101092052.
      </p>
    </div>
  </CFooter>
</template>

<style scoped>
.app-footer {
  background: #2f3338;
  border-top: 0;
  color: #e7e9ec;
}

.footer-content {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
}

.footer-main {
  align-items: center;
  display: flex;
  gap: 2rem;
  justify-content: center;
  width: 100%;
}

.footer-logo-wrap {
  align-items: center;
  display: flex;
}

.footer-logo-wrap-right {
  justify-content: center;
}

.footer-logo {
  display: block;
  height: auto;
  object-fit: contain;
}

.footer-logo-eu {
  max-width: 310px;
}

.footer-logo-buildchain {
  max-width: 220px;
}

.footer-link-row {
  color: #e7e9ec;
  font-size: 0.95rem;
  margin: 0;
  text-align: center;
  width: 100%;
}

.footer-link-row a {
  color: #ff8652;
  text-decoration: none;
}

.footer-link-row a:hover,
.footer-link-row a:focus {
  text-decoration: underline;
}

.footer-funding {
  color: #ff8652;
  font-size: 0.95rem;
  letter-spacing: 0.03em;
  margin: 0;
  text-align: center;
  width: 100%;
}

@media (max-width: 991px) {
  .footer-main {
    gap: 1.5rem;
  }
}

@media (max-width: 575px) {
  .app-footer {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }

  .footer-logo-eu {
    max-width: 260px;
  }

  .footer-logo-buildchain {
    max-width: 180px;
  }

  .footer-main {
    align-items: center;
    flex-direction: column;
  }

  .footer-logo-wrap-right {
    justify-content: center;
  }

  .footer-link-row {
    font-size: 0.85rem;
  }

  .footer-funding {
    font-size: 0.85rem;
    text-align: center;
  }
}
</style>
