allprojects { repositories { google(); mavenCentral() } }

val outputBuildDir = rootProject.layout.buildDirectory.dir("../../build").get()
rootProject.layout.buildDirectory.value(outputBuildDir)
subprojects {
    layout.buildDirectory.value(outputBuildDir.dir(project.name))
    evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") { delete(rootProject.layout.buildDirectory) }
