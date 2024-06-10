<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
                xmlns:spec="http://www.schemaTest.org/train"
                version="1.0">

<xsl:template match="/">
<html>
  <body>
     <xsl:apply-templates select="spec:BOOKS/spec:PLAY"/>
  </body>
</html>
</xsl:template>

<xsl:template match="spec:BOOKS/spec:PLAY">
   <h1><xsl:value-of select="spec:TITLE"/></h1>
   <xsl:apply-templates select="spec:FM"/>
   <xsl:apply-templates select="spec:PERSONAE"/>
   <xsl:apply-templates select="spec:SCNDESCR"/>
   <xsl:apply-templates select="spec:PLAYSUBT"/>
   <xsl:apply-templates select="spec:INDUCT"/>
   <xsl:apply-templates select="spec:PROLOGUE"/>
   <xsl:apply-templates select="spec:ACT"/>
</xsl:template>

<xsl:template match="spec:FM">
<h4>Acknowledgement</h4>
<p><xsl:for-each select="spec:P">
      <xsl:value-of select="."/><br/>
   </xsl:for-each>
</p>
</xsl:template>

<xsl:template match="spec:PERSONAE">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="//spec:PERSONAE/spec:TITLE">
   <h3><xsl:value-of select="."/></h3>
</xsl:template>

<xsl:template match="spec:SCNDESCR">
  <h3><i><xsl:value-of select="."/></i></h3>
</xsl:template>

<xsl:template match="spec:PLAYSUBT">
  <h3><i><xsl:value-of select="."/></i></h3>
</xsl:template>

<xsl:template match="spec:PROLOGUE">
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="spec:PGROUP">
  <h4><xsl:value-of select="spec:GRPDESCR"/></h4>
  <p><xsl:for-each select="spec:PERSONA">
        <i><xsl:value-of select="."/></i><br/>
     </xsl:for-each>
  </p>
</xsl:template>

<xsl:template match="spec:PERSONA">
   <i><xsl:value-of select="."/></i><br/>
</xsl:template>

<xsl:template match="spec:ACT">
   <h4><xsl:value-of select="spec:TITLE"/></h4>
   <xsl:apply-templates select="spec:SCENE"/>

</xsl:template>

<xsl:template match="spec:SCENE">
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="//spec:SCENE/spec:TITLE">
   <h4><xsl:value-of select="."/></h4>
</xsl:template>

<xsl:template match="spec:SPEECH">
   <table>
      <tr valign="top">
         <td><b><xsl:value-of select="spec:SPEAKER"/></b></td>
         <td><xsl:apply-templates/></td>
      </tr>
   </table>
</xsl:template>

<xsl:template name="SPEAK">
   <xsl:param name="PERSON"/>
   <b><xsl:value-of select="$PERSON"/></b>
</xsl:template>

<xsl:template match="//spec:SPEECH/spec:LINE">
   <xsl:variable name="RevText">	
     <xsl:call-template name="encryptText">
        <xsl:with-param name="normalVerse" select="."/>
     </xsl:call-template>
   </xsl:variable>
   <xsl:value-of select="$RevText"/><br/>
</xsl:template>

<xsl:template name="encryptText">
   <xsl:param name="normalVerse"/>
   <xsl:param name="backwardsText" select="Empty"/>
   <xsl:choose>
      <xsl:when test="string-length($normalVerse) = 0">
         <xsl:value-of select="$backwardsText"/>
      </xsl:when>
      <xsl:otherwise>
         <xsl:call-template name="encryptText">
            <xsl:with-param name="normalVerse" select="substring($normalVerse,2,string-length($normalVerse)-1)"/>
            <xsl:with-param name="backwardsText" select="concat(substring($normalVerse,1,1),$backwardsText)"/>
         </xsl:call-template>
      </xsl:otherwise>
   </xsl:choose>
</xsl:template>

<xsl:template match="//spec:STAGEDIR">
   <i><xsl:value-of select="."/></i><br/>
</xsl:template>

<xsl:template match="//spec:SUBHEAD">
   <b><i><xsl:value-of select="."/></i></b><br/>
</xsl:template>

<xsl:template match="spec:EPILOGUE">
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="spec:INDUCT">
   <h3><xsl:value-of select="spec:TITLE"/></h3>
   <xsl:apply-templates select="spec:SCENE"/>
</xsl:template>

</xsl:stylesheet>
