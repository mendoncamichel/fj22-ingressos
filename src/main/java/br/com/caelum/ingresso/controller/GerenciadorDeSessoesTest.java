package br.com.caelum.ingresso.controller;


import java.time.Duration;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Assert;
import org.junit.Test;

import br.com.caelum.ingresso.model.Filme;
import br.com.caelum.ingresso.model.Sala;
import br.com.caelum.ingresso.model.Sessao;

public class GerenciadorDeSessoesTest {
	@Test
	public void verificaSePodeCadastrarDuasSessoesSemHorariosConflitantes(){
		
		Sala sala = new Sala("Sala1");
		Filme filme = new Filme("Transformers",Duration.ofMinutes(120),"Sci-fi");
		Sessao sessao = new Sessao (sala,filme,LocalTime.parse("12:45"));
		List <Sessao> sessoes = Arrays.asList(new Sessao(sala,filme,LocalTime.parse("18:45")));
		
		GerenciadorDeSessoes gerenciador = new GerenciadorDeSessoes(sessoes);
							Assert.assertTrue(gerenciador.cabe(sessao));
	}

}
